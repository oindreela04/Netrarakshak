import type { Metadata } from "next";
import { PageHero, Prose } from "@/components/marketing/page-hero";
export const metadata: Metadata = { title: "AI technology" };

export default function Technology() {
  return (
    <>
      <PageHero title="Disease-specific models, measured honestly" intro="How NetraRakshak's AI is built, evaluated and constrained — and what it does not do." />
      <Prose>
        <h2>One model per disease</h2>
        <p>There is no single model that &ldquo;detects everything&rdquo;. Each condition is an independent module with its own labelled data,
          architecture, held-out evaluation and activation switch. A module that has not been trained and evaluated stays switched off,
          and the screening is routed straight to the ophthalmologist.</p>
        <h2>Diabetic retinopathy grading</h2>
        <p>The first module grades colour fundus photographs on the International Clinical Diabetic Retinopathy scale: no apparent
          retinopathy, mild, moderate and severe non-proliferative, and proliferative DR.</p>
        <ul>
          <li>Pre-processing crops the retinal field, normalises illumination and resizes consistently for training and inference.</li>
          <li>An ImageNet-pretrained convolutional network is fine-tuned with patient-grouped, grade-stratified splits so the same patient never appears in both training and test data.</li>
          <li>Class imbalance is handled with weighted loss or balanced sampling. Model selection uses quadratic weighted kappa on a validation set.</li>
          <li>Confidence is calibrated with temperature scaling on the validation set.</li>
          <li>Accuracy, precision, recall, F1, sensitivity, specificity, ROC-AUC and the confusion matrix are computed on a separate test set and written to the model card automatically.</li>
        </ul>
        <h2>Uncertainty and explainability</h2>
        <p>If the top-class confidence is below threshold or the prediction entropy is high, the result is shown as
          <strong> INCONCLUSIVE — HUMAN REVIEW REQUIRED</strong>. Grad-CAM heatmaps show which regions influenced the model. They are
          labelled as model explainability and are never presented as lesions or confirmed findings.</p>
        <h2>Image quality first</h2>
        <p>Before any model runs, each photograph is checked for resolution, retinal visibility, field of view, brightness, contrast,
          exposure, blur, focus and artefacts, and for whether it looks like a colour fundus photograph at all. Images that fail are not analysed.</p>
        <h2>What NetraRakshak does not do</h2>
        <ul>
          <li>It does not make autonomous diagnoses. Every case is reviewed and signed by an ophthalmologist.</li>
          <li>It does not diagnose stroke, cataract or systemic disease from a fundus photograph.</li>
          <li>It does not replace a fundus camera with a phone camera. Only images from compatible retinal fundus cameras are supported.</li>
          <li>It has not been clinically validated or approved by CDSCO. Published metrics will always state the dataset they were measured on.</li>
        </ul>
        <h2>Fundus camera integration</h2>
        <p>Images can be uploaded from any camera that exports JPEG, PNG or TIFF. For Professional and Enterprise customers, a capture
          agent installed at the screening station watches the camera&apos;s export folder or uses the manufacturer&apos;s documented SDK or
          DICOM interface to send images directly into the right screening session.</p>
      </Prose>
    </>
  );
}
