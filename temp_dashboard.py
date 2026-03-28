from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import os

app = FastAPI()

@app.get("/dashboard_real")
async def dashboard_real(request: Request):
    """真实产品界面"""
    # 读取我们创建的HTML文件
    html_path = "/root/.openclaw/workspace/AICostMonitor/templates/dashboard_real.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return Response(content=html_content, media_type="text/html")
    else:
        return Response(content="<h1>产品界面开发中...</h1><p>即将推出完整功能</p>", media_type="text/html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
