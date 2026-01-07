# Testing Guide - AI Course Creator

## Prerequisites
- Docker Desktop running
- Port 3000 available
- `data1` folder present in repo root

## 1. Startup
Run the startup script:
```bash
./start.sh
```
- Choose Option 2 (Background).
- Wait for "✅ Services started successfully!".
- Open Browser: [http://localhost:3000](http://localhost:3000)

## 2. Phase 1 Verification (Syllabus -> Blueprint)
1.  **Landing Page**: You should see "Phase-1" / "Phase-2" header.
2.  **Step 1 (Selection)**:
    - Click "Select from Template".
    - You should see a list of preloaded syllabi (e.g., "Software Engineering", "Machine Learning").
    - Select one and click "Next".
3.  **Step 2 (Blueprint Review)**:
    - Verify the "Blueprint" tree loads.
    - Click a Module to expand.
    - Edit a "Module Outcome" text.
    - Edit a "Duration" value.
    - Click "Confirm & Next".

## 3. Phase 2 Verification (Input -> Output)
4.  **Step 3 (Knowledge / References)**: (Note: Moved before Specs)
    - Select Scope: "Module".
    - Choose a Module (e.g., Module 1).
    - Upload a dummy PDF or DOCX.
    - Verify it appears in the list as "INDEXED" (or processing).
    - Click "Next".
5.  **Step 4 (Specs / Constraints)**:
    - Adjust "Global Defaults" (e.g., set slides to 10).
    - Click "Save & Next".
6.  **Step 5 (Prompt)**:
    - Click "Generate Optimized Prompt".
    - Wait for AI generation (or mock fallback if API key missing).
    - Verify prompt text appears.
    - Click "Validate & Generate Preview".
7.  **Step 6 (Review / Preview)**:
    - Wait for PPT preview generation.
    - Click "Approve" to proceed to final generation.
8.  **Step 7 (Finalize)**:
    - Click "Generate Final Content".
    - Download the resulting PPTX/PDF.

## 4. Troubleshooting
- **White Page?**: Refresh. If persistent, check console logs. An ErrorBoundary should show details.
- **Backend Error?**: Run `cd infra && docker-compose logs course-lifecycle` to see API errors.
