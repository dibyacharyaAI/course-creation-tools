# Frontend HITL Verification Checklist

This document guides the manual verification of the "Topic Queue" HITL UI.

## Prerequisites
- Backend service running: `python3 -m uvicorn services.course-lifecycle.app.main:app --reload`
- Frontend dev server running: `npm run dev` (in `frontend/` directory)
- Database initialized and seeded (or fresh).

## Verification Steps

### 1. Navigation to Step 6
1.  Complete Steps 1-5 of the wizard as usual.
2.  On Step 5 (Prompt), click "Next" or "Generate".
3.  Ensure you land on **Step 6: Topic Queue**.
    - **Expected**: A split-screen UI. Left panel list of topics. Right panel "Select a topic".

### 2. Topic List & Status
1.  Check the left panel.
    - **Expected**: List of all topics defined in the Blueprint (Step 2).
    - **Expected**: Badges showing status (e.g., `NOT_STARTED` or `PENDING`).

### 3. Generate Slides (Per Topic)
1.  Click on a topic in the list.
2.  In the right panel, click **Generate**.
3.  Wait for completion.
    - **Expected**: Status updates to `GENERATED`.
    - **Expected**: "Preview PPT" tab shows a Success message with a mocked PPTX path.
    - **Expected**: "Verification" block appears showing "Run Checks".

### 4. Edit JSON
1.  Switch to the **Edit JSON** tab.
2.  Modify the JSON content (e.g., change `"title": "Old Title"` to `"title": "Edited Title"`).
3.  Click **Save & Verify**.
    - **Expected**: Spinner appears.
    - **Expected**: Status updates to `VERIFIED` (if min slides met) or `REJECTED` (if not).
    - **Expected**: Version number increments in the header (e.g., v1 -> v2).

### 5. Verification Logic
1.  If status is `GENERATED` or `PENDING`, click **Run Checks**.
    - **Expected**: Status updates to `VERIFIED` (mock assumes success if slide count >= 8).

### 6. Approval
1.  Once `VERIFIED`, click **Approve** in the footer.
2.  Refresh the page.
    - **Expected**: Topic status persists as `APPROVED` (Green badge).
    - **Expected**: Approve button is disabled/indicated as approved.

### 7. Rejection
1.  Select another topic.
2.  Click **Reject**.
3.  **Expected**: Status updates to `REJECTED` (Red badge).

## Completion
- Completion of all topics is not strictly enforced by the UI yet (Verify: Can you click Next? The `onNext` callback handles global completion, but currently Step 6 only approves per topic).
- *Note*: Blocking global "Next" until all topics are approved is a backend constraint enforced at final content generation time, or can be added to UI later.
