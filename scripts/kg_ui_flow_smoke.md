# Knowledge Graph UI Flow Smoke Test

## Pre-requisites
- Backend running (`infra-course-lifecycle-1`)
- Frontend running (`frontend`)
- Browser accessible at `http://localhost:3000`

## Test Steps

### 1. Topic Generation & Graph Sync
1. Navigate to **Step 6 (Review)**.
2. Observe "Topic Queue (KG)" list.
3. If list is empty:
    - Click **"Sync"** button (top right of list) OR
    - Click **"Build Graph from Blueprint"** (center).
4. Select a Topic.
5. If status is "Not Started", click **"Generate Content"**.
6. Wait for generation. The list should update status to "GENERATED".

### 2. Preview & Export
1. Select a "GENERATED" topic.
2. In "Preview" tab, ensure slides are visible in "Slide Content Preview".
3. Click **"Download PPT"**.
    - Expect: New tab opens with PPTX download (or mock JSON if renderer offline).
4. Click **"Preview PDF"**.
    - Expect: New tab opens with PDF download.

### 3. Editing (Knowledge Graph Patch)
1. Switch to **"Edit JSON (KG)"** tab.
2. Modify a bullet point (e.g., change "Point 1" to "EDITED Point 1").
3. Click **"Save to Graph"**.
4. Switch back to **"Preview"** tab.
5. Verify the text matches "EDITED Point 1".

### 4. Approval
1. In the Footer, enter a comment "Looks good".
2. Click **"Approve"**.
3. Verify status badge changes to **APPROVED** (Green).
4. Verify the topic list shows Green badge.

## Troubleshooting
- If "Sync" fails: Check backend logs for `GraphBuilder` errors.
- If "Download PPT" fails: Check `export.py` logs or `ppt-renderer` service status.
