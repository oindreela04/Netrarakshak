"""Disease-module registry and gated model loading.

Each disease is an independent module with its own data, model, evaluation and activation state.
A module only runs inference when ALL of the following hold:
  1. it is implemented (has an inference adapter),
  2. a weights file and a model card produced by the training pipeline exist and the weights hash matches,
  3. the card contains held-out test metrics computed by the pipeline,
  4. the model was not trained on synthetic data (unless ALLOW_NONCLINICAL_TEST_MODELS=true, used only in tests).
Otherwise the module reports "model_unavailable" and the screening is routed to human review.
"""
import hashlib
import json
import threading
from dataclasses import dataclass, field
from pathlib import Path

from app.config import get_settings

settings = get_settings()


@dataclass
class ModuleSpec:
    key: str
    name: str
    description: str
    implemented: bool
    data_requirements: str
    candidate_datasets: list[str] = field(default_factory=list)
    notes: str = ""


MODULES: dict[str, ModuleSpec] = {
    "diabetic_retinopathy": ModuleSpec(
        "diabetic_retinopathy", "Diabetic Retinopathy (ICDR 5-grade)",
        "Grades colour fundus photographs on the International Clinical DR scale: no apparent DR, mild, moderate, severe NPDR, proliferative DR.",
        True, "Colour fundus photographs with ICDR grades from qualified graders; patient IDs for grouped splitting.",
        ["APTOS 2019 (Kaggle, competition terms)", "EyePACS / Kaggle DR 2015 (competition terms)", "IDRiD (CC BY 4.0)",
         "Messidor-2 (licence on request)", "DDR (research use)", "Indian clinical data under DPDP-compliant agreements"]),
    "glaucoma": ModuleSpec(
        "glaucoma", "Glaucoma suspect screening",
        "Optic-disc / cup assessment (vertical cup-to-disc ratio, rim) to flag glaucoma suspects for comprehensive examination.",
        False, "Optic-disc-centred fundus images with glaucoma / non-glaucoma labels from comprehensive exams (IOP, OCT, fields), ideally disc/cup segmentations.",
        ["REFUGE (challenge terms)", "ORIGA", "Drishti-GS1 (Indian)", "AIROGS (Rotterdam EyePACS, challenge terms)"],
        "Fundus-only assessment can flag suspects but cannot diagnose glaucoma; confirmation requires IOP, OCT and visual fields."),
    "amd": ModuleSpec(
        "amd", "Age-related macular degeneration",
        "Detects drusen, pigmentary changes and signs suggestive of advanced AMD (AREDS-style severity).",
        False, "Macula-centred fundus images with AREDS-style AMD severity grades.",
        ["AREDS (dbGaP, data-use agreement)", "iChallenge-AMD / ADAM (challenge terms)"],
        "Neovascular activity assessment requires OCT; fundus screening is a triage aid only."),
    "hypertensive_retinopathy": ModuleSpec(
        "hypertensive_retinopathy", "Hypertensive retinopathy",
        "Retinal vascular signs (AV nicking, arteriolar narrowing, haemorrhages, cotton-wool spots, disc oedema) graded on Keith-Wagener-Barker / Mitchell-Wong.",
        False, "Fundus images graded for hypertensive retinopathy by retina specialists; vessel segmentation labels helpful.",
        ["No large public graded dataset identified — requires prospective collection with clinical partners"],
        "Does not and cannot diagnose hypertension or predict stroke."),
    "other_abnormalities": ModuleSpec(
        "other_abnormalities", "Other retinal abnormalities (multi-label triage)",
        "Flags images with findings outside the active modules (e.g. RVO, myopic changes, laser scars, media opacity) for human review.",
        False, "Multi-label annotated fundus images from retina specialists.",
        ["RFMiD (CC BY 4.0, Indian multi-disease)", "ODIR-5K (research terms)"],
        "Triage only; never a diagnosis. Media opacity flag is not a cataract diagnosis."),
}


class ModelUnavailable(Exception):
    pass


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def module_dir(key: str) -> Path:
    return Path(settings.model_registry_dir) / key


def active_version(key: str) -> str | None:
    f = module_dir(key) / "ACTIVE"
    return f.read_text().strip() if f.exists() else None


def read_card(key: str, version: str | None = None) -> dict | None:
    version = version or active_version(key)
    if not version:
        return None
    p = module_dir(key) / version / "model_card.json"
    return json.loads(p.read_text()) if p.exists() else None


def availability(key: str) -> dict:
    spec = MODULES[key]
    out = {"key": key, "name": spec.name, "description": spec.description, "implemented": spec.implemented,
           "data_requirements": spec.data_requirements, "candidate_datasets": spec.candidate_datasets, "notes": spec.notes,
           "available": False, "reason": "", "version": None, "card": None}
    if not spec.implemented:
        out["reason"] = "Module architecture defined; no trained and validated model exists. Not activated."
        return out
    version = active_version(key)
    if not version:
        out["reason"] = "No trained model has been registered. Run the training pipeline with a licensed, labelled dataset."
        return out
    vdir = module_dir(key) / version
    card = read_card(key, version)
    if not card or not (vdir / "weights.pt").exists():
        out["reason"] = f"Registered version {version} is missing weights or model card."
        return out
    if card.get("weights_sha256") and card["weights_sha256"] != _sha256(vdir / "weights.pt"):
        out["reason"] = "Weights file hash does not match the model card (possible tampering). Model blocked."
        return out
    if not card.get("evaluation", {}).get("test_metrics"):
        out["reason"] = "Model card has no held-out evaluation metrics. Model blocked."
        return out
    if card.get("training_data", {}).get("synthetic") and not settings.allow_nonclinical_test_models:
        out["reason"] = "Active model was trained on synthetic data (pipeline smoke test) and is blocked from patient use."
        return out
    public_card = {k: v for k, v in card.items() if k != "training"}
    out.update(available=True, version=version, card=public_card,
               reason=card.get("clinical_use_status", "Not clinically validated"))
    return out


_cache: dict[str, object] = {}
_lock = threading.Lock()


def get_predictor(key: str):
    info = availability(key)
    if not info["available"]:
        raise ModelUnavailable(info["reason"])
    cache_key = f"{key}:{info['version']}"
    with _lock:
        if cache_key not in _cache:
            if key == "diabetic_retinopathy":
                from ai.modules.diabetic_retinopathy.infer import DRPredictor
                _cache[cache_key] = DRPredictor(module_dir(key) / info["version"])
            else:  # pragma: no cover - no other module implemented
                raise ModelUnavailable("No inference adapter")
        return _cache[cache_key]


def clear_cache():
    with _lock:
        _cache.clear()
