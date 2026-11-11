# User manual (draft)

## Receptionist
1. **Patients → Register patient.** Enter name, date of birth (age is calculated), contact details and medical
   history. Tick the consents the patient has given and how (signed form / digital / verbal witnessed).
2. To record a later consent or withdrawal: open the patient → **Consent** tab.

## Screening technician
1. **New screening** → choose the patient → enter the camera model and dilation status → **Start screening**.
2. Capture the right eye on the fundus camera and drop the file on **Right eye (OD)**; repeat for **Left eye (OS)**.
3. Read the quality result. *Recapture required* explains why (e.g. blur, too dark). Recapture and use **Replace image**.
4. Click **Run AI screening**. If no AI model is active, the case goes to the ophthalmologist for manual grading.
5. If the doctor requests recapture, the screening shows the reason; upload new images and run AI screening again.

## Ophthalmologist
1. **Review queue** lists cases; AI-suggested referable and inconclusive cases come first.
2. In the workspace, inspect images (scroll to zoom, drag to pan, double-click to toggle zoom, *OD + OS* for both
   eyes, *Grad-CAM overlay*/*Heatmap* and *Compare*). Heatmaps are not lesion maps.
3. For each eye choose **Accept AI**, **Modify** or **Reject AI**, and set the final grade, DME suspicion and notes.
4. Add impression, recommendations, referral and next screening interval. **Save draft** at any time.
5. **Approve and sign**: confirm the attestation and re-enter your password. The screening is locked.
6. Open the screening → **Generate signed report**. View, print or download the PDF.

## Hospital administrator
Team (users, roles, password resets), Hospital (profile, branding, logo, branches, retention), Subscription (plan,
usage, invoices), Audit log, Analytics.

## Status meanings
Awaiting images · Ready for analysis · Awaiting review · In review · Recapture requested · Signed · Reported.

## Important
AI results are suggestions from software that is not clinically validated. Never act on a report marked DRAFT.
