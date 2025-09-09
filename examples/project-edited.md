# 🧠 Custom UI for n8n Workflows

This project outlines how to build a custom front-end UI that interacts with [n8n](https://n8n.io/) workflows using webhooks and wait nodes. This allows developers to create interactive, multi-step workflows while keeping the user experience smooth and responsive.

---

## 📅 Overview

**Goal:** Build a two-way interaction between a front-end UI and an n8n workflow using webhooks and wait nodes, with JSON responses shared between both layers.

---

## 🛠️ File Structure

```bash
project/
├── index.js         # Express backend (Node app)
├── public/
│   └── index.html   # Frontend UI
```

In `index.js`, serve static files like so:

```js
const express = require('express');
const app = express();
const port = 3000;

app.use(express.static('public'));

app.listen(port, () => {
  console.log(`App listening at http://localhost:${port}`);
});
```

---

## 📈 How It Works

### 1. Initial Frontend Trigger ➞ n8n Webhook

- User clicks a button in the UI.
- This sends a request to your Express backend.
- Your backend then POSTs to an **n8n webhook URL**.
- n8n processes and replies using `Respond to Webhook`, including a `resumeUrl`:

```json
{
  "resumeUrl": "https://your-n8n-server.com/webhook/wait/123abc"
}
```

- Store this URL on the frontend for the next step.

---

### 2. Resume Workflow with User Input

- When the user submits a form, upload, or selection:
  - POST to the stored `resumeUrl` **via the backend**, including the required data.

### Notes:

- Backend must forward requests (with proper headers) to the `resumeUrl`.
- For files: use `multipart/form-data`.

---

### 3. Continue Workflow in n8n

In n8n:

- `Wait Node` is triggered by `resumeUrl`
- Add processing steps (logic, AI, etc.)
- End with a `Respond to Webhook` node

Example response:

```json
{
  "result": "Processed successfully",
  "nextAction": "show_summary"
}
```

Frontend receives this and updates the UI accordingly.

---

## 💡 Developer Checklist

### Frontend:

- Loads from `/public/index.html`
- Sends API requests to backend (not directly to n8n)
- Stores and uses `resumeUrl`
- Displays JSON responses to the user

### Backend (Express):

- Serves static HTML
- Proxies POST requests to n8n (both webhook and resumeUrl)
- Handles CORS implicitly
- **File uploads:** Stream request body directly with `duplex: 'half'`
- Pass resumeUrl via query parameter to avoid body parsing conflicts

### n8n:

- Webhook node triggers on first action
- Responds with `resumeUrl` key in JSON
- Uses Wait node ("Respond via Webhook")
- Ends with Respond to Webhook node with structured JSON

---

## 📂 File Upload Notes

### Working Method - Direct Stream Forwarding

**CRITICAL: No File Storage, No Uploads Folder**
- Files must be streamed directly from frontend → backend → n8n
- Never save files to disk, uploads folder, or any intermediate storage
- Never use multer, file parsing, or FormData recreation

**Frontend:**
- Use `FormData` to send files via `multipart/form-data`
- Send to backend endpoint with `resumeUrl` as query parameter
- Files go directly from user's browser to n8n via backend proxy

**Backend (Critical Implementation):**
```javascript
app.post('/api/resume-workflow', async (req, res) => {
    const resumeUrl = req.query.resumeUrl;
    
    // Stream request body directly to n8n with duplex option
    const response = await fetch(resumeUrl, {
        method: 'POST',
        body: req,           // Pass entire request object - NO FILE STORAGE
        duplex: 'half',      // Required for Node.js streaming
        headers: {
            'Content-Type': req.headers['content-type'],
            'Content-Length': req.headers['content-length']
        }
    });
});
```

**Key Learnings:**
- ✅ **DO:** Stream the entire Express `req` object directly to n8n
- ✅ **DO:** Include `duplex: 'half'` option for Node.js streaming
- ✅ **DO:** Forward original Content-Type and Content-Length headers
- ✅ **DO:** Treat backend as a transparent proxy only
- ❌ **DON'T:** Use multer or ANY file storage middleware
- ❌ **DON'T:** Create uploads folder or save files to disk
- ❌ **DON'T:** Recreate FormData in backend (causes corruption)
- ❌ **DON'T:** Try to parse multipart data manually
- ❌ **DON'T:** Use temporary files or file system operations

**Why This Works:**
- Eliminates file corruption from re-encoding
- Preserves original multipart boundaries
- **Zero file storage** - completely stateless backend
- Direct pipe from frontend → backend → n8n
- Backend acts as transparent proxy only

**🚨 CRITICAL WARNING:**
Never create an `uploads/` folder or save files anywhere. The backend must be a pure streaming proxy with no file system operations.

---

## ✅ Summary

| Component     | Role                              |
| ------------- | --------------------------------- |
| `index.html`  | User interface                    |
| `index.js`    | Backend to proxy API calls to n8n |
| `Webhook URL` | Initial trigger for workflow      |
| `resumeUrl`   | Continues workflow from Wait node |
| `Respond`     | Final response shown to user      |

---

## 🧩 LLM Agent Instruction

> "Build a front-end that starts a multi-step interaction with an n8n workflow. Use a backend (Express) to proxy the front-end's requests to avoid CORS. Follow the JSON response flow as documented. Expect `resumeUrl` in the response, and send all future interactions to that URL. The n8n workflow ends with a Respond to Webhook node returning a JSON payload to display or process."

---

Let me know if you need a starter code template or visual diagram for this flow.

