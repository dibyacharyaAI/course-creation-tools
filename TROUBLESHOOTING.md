# Troubleshooting Guide

## Common Issues

### 1. White Page / Blank Screen
- **Cause**: Usually a frontend React error or API failure during initial load.
- **Fix**:
    - Refresh the page.
    - We have added an **ErrorBoundary**. If you see a red error box, click "Reload".
    - Check Browser Console (F12) for specific JS errors.

### 2. "Docker not found" or Startup Fails
- **Cause**: Docker Desktop is not running or not in PATH.
- **Fix**:
    - Open Docker Desktop application.
    - Ensure `docker info` works in terminal.
    - If `./start.sh` fails, try running: `export PATH="/Applications/Docker.app/Contents/Resources/bin:$PATH"` before running it.

### 3. "Address already in use" (Port 3000)
- **Cause**: Another service is using port 3000.
- **Fix**:
    - Stop other services.
    - Check what is using the port: `lsof -i :3000`
    - Kill the process: `kill -9 <PID>`

### 4. Templates Not Loading (Step 1)
- **Cause**: Backend failed to read `/app/data1/manifest.json`.
- **Fix**:
    - Check logs: `cd infra && docker-compose logs course-lifecycle`
    - Verify `data1` folder exists in repo root.
    - Ensure `manifest.json` is valid JSON.

### 5. AI Generation Fails
- **Cause**: Missing `GEMINI_API_KEY` or API quota exceeded.
- **Fix**:
    - Check `.env` file in `infra/` or repo root.
    - Verify API key valid.
    - The system may fall back to mock data if AI fails (check logs).

## Support
For deep debugging, view logs of all services:
```bash
cd infra
docker-compose logs -f
```
