import { defineConfig } from '@hey-api/openapi-ts'

// ARCHITECTURE §2.5 — the entire client and all wire types are generated
// from FastAPI's /openapi.json into src/api/generated (SSOT). Interceptors
// (JWT + silent refresh) are mounted on the exported client instance by
// src/store/auth.ts at app bootstrap.
export default defineConfig({
  // Regenerate with: (backend) python -c "import json; from app.main import app;
  // print(json.dumps(app.openapi()))" > ../frontend/openapi.json && npm run generate:api
  input: './openapi.json',
  output: 'src/api/generated',
  plugins: ['@hey-api/client-axios'],
})
