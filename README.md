# 脱口秀票务 MCP Server

## 部署到 Vercel

### 1. 上传到 GitHub
把这个文件夹推到你的 GitHub 仓库。

### 2. 在 Vercel 导入项目
- 登录 vercel.com
- 点 "Add New Project"
- 选择你的 GitHub 仓库
- 点 Deploy

### 3. 配置环境变量
在 Vercel 项目 → Settings → Environment Variables 添加：

| Key | Value |
|-----|-------|
| YOUZAN_CLIENT_ID | 你的 client_id |
| YOUZAN_CLIENT_SECRET | 你的 client_secret（重置后的新版） |
| YOUZAN_KDT_ID | 你的店铺ID（在有赞后台店铺设置里找） |

### 4. 重新部署
添加环境变量后点 Redeploy。

### 5. 你的 MCP 地址
部署成功后地址是：
```
https://你的项目名.vercel.app/mcp
```

把这个地址填入 Coze 的 Skill 配置即可。

## 本地测试
```bash
pip install requests
YOUZAN_CLIENT_ID=xxx YOUZAN_CLIENT_SECRET=xxx YOUZAN_KDT_ID=xxx python -c "
from api.mcp import get_shows
print(get_shows({}))
"
```
