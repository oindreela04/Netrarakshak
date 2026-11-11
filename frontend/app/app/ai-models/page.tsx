"use client";
import { useFetch } from "@/lib/use-fetch";
import { pct } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Table, Td, Th } from "@/components/ui/table";
import { Loading, PageHeader } from "@/components/app/bits";

export default function AIModules() {
  const { data, loading } = useFetch<any[]>("/ai/modules");
  return (
    <>
      <PageHeader title="AI modules" description="Each disease is a separate module with its own data, model and evaluation. A module only runs when a trained, evaluated model is registered." />
      {loading || !data ? <Loading /> : (
        <div className="space-y-6">
          {data.map((m) => (
            <Card key={m.key}>
              <CardHeader title={m.name} description={m.description}
                action={m.available ? <Badge tone="ok">Active · v{m.version}</Badge> : m.implemented ? <Badge tone="warn">No trained model</Badge> : <Badge>Not activated</Badge>} />
              <CardBody className="space-y-4 text-sm">
                <p className={m.available ? "text-clinical-600" : "text-warn"}>{m.reason}</p>
                <div className="grid gap-4 md:grid-cols-2">
                  <div><p className="font-medium text-navy">Data requirements</p><p className="mt-1 text-slate">{m.data_requirements}</p></div>
                  <div><p className="font-medium text-navy">Candidate datasets (licence to be verified per use)</p><ul className="mt-1 list-disc pl-5 text-slate">{m.candidate_datasets.map((d: string) => <li key={d}>{d}</li>)}</ul></div>
                </div>
                {m.notes && <p className="text-xs text-slate">{m.notes}</p>}
                {m.card && <ModelCard card={m.card} />}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </>
  );
}

function ModelCard({ card }: { card: any }) {
  const t = card.evaluation.test_metrics;
  return (
    <div className="rounded-md border border-line">
      <div className="border-b border-line bg-mist px-4 py-2.5 text-sm"><b className="text-navy">Model card</b> · {card.model_name} · trained on {card.training_data.name} ({card.training_data.licence}) · test set n = {t.n}</div>
      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs text-slate">Held-out test metrics, computed by the training pipeline</p>
          <Table><tbody>
            {[["Accuracy", t.accuracy], ["Macro precision", t.macro_precision], ["Macro recall (sensitivity)", t.macro_recall], ["Macro F1", t.macro_f1],
              ["Quadratic weighted kappa", t.quadratic_weighted_kappa], ["ROC-AUC (macro, one-vs-rest)", t.roc_auc_macro_ovr],
              ["Referable DR sensitivity", t.referable?.sensitivity], ["Referable DR specificity", t.referable?.specificity], ["Referable DR ROC-AUC", t.referable?.roc_auc],
              ["Calibration error (ECE) after scaling", t.ece_after_calibration]].map(([k, v]) => (
              <tr key={k as string}><Td className="py-1.5 text-slate">{k}</Td><Td className="tabular py-1.5 text-right">{k === "Quadratic weighted kappa" ? (v as number)?.toFixed(3) ?? "—" : pct(v as number)}</Td></tr>))}
          </tbody></Table>
        </div>
        <div>
          <p className="mb-2 text-xs text-slate">Confusion matrix (rows: reference grade, columns: predicted)</p>
          <div className="overflow-x-auto"><table className="tabular text-xs"><tbody>
            <tr><td /> {t.class_names.map((c: string) => <td key={c} className="px-1.5 pb-1 text-center text-slate">{c.split(" ")[0]}</td>)}</tr>
            {t.confusion_matrix.map((row: number[], i: number) => {
              const max = Math.max(1, ...t.confusion_matrix.flat());
              return <tr key={i}><td className="pr-2 text-slate">{t.class_names[i]}</td>{row.map((v, j) => <td key={j} className="h-9 w-12 border border-white text-center" style={{ background: `rgba(31,111,178,${v / max})`, color: v / max > 0.5 ? "white" : "#14202E" }}>{v}</td>)}</tr>;
            })}
          </tbody></table></div>
          <p className="mt-3 text-xs font-medium text-warn">{card.clinical_use_status}</p>
          <ul className="mt-2 list-disc pl-5 text-xs text-slate">{card.limitations?.map((l: string) => <li key={l}>{l}</li>)}</ul>
        </div>
      </div>
    </div>
  );
}
