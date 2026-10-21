# qianlink 自动注册并导出订阅

使用 Playwright 自动打开注册页，用 `mail.txt` 里的 Outlook 邮箱收验证码完成注册，进入控制台后点击“默认线路 → 二维码”，把里面的订阅内容保存到 `data.txt`，并通过 GitHub Actions 定时运行、自动提交回仓库。

> 请仅在已获得服务方许可的前提下使用。仓库务必设为**私有**，`data.txt` 里是订阅链接。

## 文件说明

| 文件 | 作用 |
| --- | --- |
| `register.py` | 主脚本：注册、收验证码、提取订阅内容 |
| `.github/workflows/register.yml` | Actions 工作流 |
| `requirements.txt` | Python 依赖（playwright、requests） |
| `mail.txt.example` | 邮箱文件格式示例 |
| `data.txt` | 运行产物：每行一个账号的订阅内容 |
| `done.txt` | 运行产物：已处理过的邮箱，下一轮会跳过 |

## mail.txt 格式

每行一个账号，用 `----` 分隔：

```
邮箱----密码----client_id----refresh_token----分组
```

脚本只用到邮箱、`client_id`、`refresh_token`，其余字段忽略。用 refresh_token 换取 access_token，再通过 Microsoft Graph 读取收件箱，取验证码（4 到 8 位数字）。

## 部署步骤

1. 把本项目文件放进你的**私有**仓库根目录。
2. 在仓库手动创建两个空文件 `data.txt` 和 `done.txt`（避免第一轮提交时报错）。
3. 进入 Settings → Secrets and variables → Actions，添加：
   - `MAIL_TXT`：`mail.txt` 的完整内容
   - `REG_PASSWORD`：统一使用的注册密码
4. 在 Actions 页面手动运行 `register`，或等待定时触发。
5. 在 Settings → Actions → General → Workflow permissions 选择 Read and write permissions，否则无法自动提交。

## 运行规则

- 工作流每 30 分钟触发一次（`cron: "*/30 * * * *"`），也支持手动触发。GitHub 定时任务最短间隔 5 分钟，且可能延迟。
- 每次最长运行 30 分钟，脚本每 2 分钟开始处理一个账号，剩余不足 1 分钟时不再开始新账号。
- `concurrency` 保证同一时间只有一个任务在运行。
- 可调参数在 `register.yml` 的 `INTERVAL`（秒）和 `DURATION`（秒）。

## 结果保存

1. 成功提取到订阅内容后，追加一行到 `data.txt`。
2. 每处理完一个账号，成功或失败，都把邮箱记入 `done.txt`。
3. 工作流最后一步（`if: always()`）提交并推送 `data.txt` 和 `done.txt`。
4. `mail.txt` 由 Secret 临时生成，提交前删除，不会进入仓库。

注意：失败的账号也会进入 `done.txt`，不会自动重试；如需重试，从 `done.txt` 中删掉对应邮箱即可。

## 需要按实际页面修改的地方

`register.py` 顶部的这一组配置是占位的，需要按真实页面调整：

- `SEL_EMAIL`、`SEL_PASSWORD`、`SEL_CODE`、`SEL_SEND`、`SEL_SUBMIT`：注册表单各元素的选择器
- `TXT_REGISTER`、`TXT_LINE`、`TXT_QR`：按钮或入口上的文字
- `SEL_QR_TEXT`：二维码弹窗中存放订阅内容的元素
- 注册成功后的跳转地址匹配：`re.compile(r"(dashboard|console|user)")`

## 常见问题

- **换取 token 或读邮件时报权限错误**：说明该 `client_id` 授权的是 IMAP 而不是 Graph，需要改成 IMAP 方式读取。
- **注册页有人机验证（CAPTCHA）**：脚本不会绕过，需要服务方放行。
- **提交失败**：检查 Workflow permissions 是否为读写，以及 `data.txt`、`done.txt` 是否存在。

## 本地运行

```bash
pip install -r requirements.txt
playwright install chromium
# 准备好 mail.txt（参考 mail.txt.example）
REG_PASSWORD=你的密码 python register.py
```
