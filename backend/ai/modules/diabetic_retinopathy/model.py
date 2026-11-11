"""Diabetic retinopathy grader: ImageNet-pretrained CNN backbone with a 5-class ICDR head."""
import torch.nn as nn
import torchvision

CLASS_NAMES = ["No apparent DR", "Mild NPDR", "Moderate NPDR", "Severe NPDR", "Proliferative DR"]
CLASS_KEYS = ["no_dr", "mild_npdr", "moderate_npdr", "severe_npdr", "proliferative_dr"]
REFERABLE_FROM = 2  # moderate NPDR or worse

ARCHS = {
    "efficientnet_b0": (torchvision.models.efficientnet_b0, torchvision.models.EfficientNet_B0_Weights.IMAGENET1K_V1),
    "efficientnet_b3": (torchvision.models.efficientnet_b3, torchvision.models.EfficientNet_B3_Weights.IMAGENET1K_V1),
    "resnet50": (torchvision.models.resnet50, torchvision.models.ResNet50_Weights.IMAGENET1K_V2),
}


def build_model(arch: str = "efficientnet_b0", num_classes: int = 5, pretrained: bool = True, dropout: float = 0.3) -> nn.Module:
    fn, weights = ARCHS[arch]
    m = fn(weights=weights if pretrained else None)
    if arch.startswith("efficientnet"):
        in_f = m.classifier[1].in_features
        m.classifier = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_f, num_classes))
    else:
        m.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(m.fc.in_features, num_classes))
    return m


def gradcam_layer(model: nn.Module, arch: str) -> nn.Module:
    return model.features[-1] if arch.startswith("efficientnet") else model.layer4[-1]
