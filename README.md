# 减重门诊管理系统（逢安堂）Streamlit Cloud 在线版 v1

本项目用于 GitHub + Streamlit Community Cloud 部署。

## 架构

- Streamlit：前端和业务界面
- Supabase PostgreSQL：云数据库
- Supabase Storage：舌象图片与资料文件
- Streamlit Secrets：登录账号、Supabase 密钥

## 快速部署

1. 创建 Supabase 项目
2. 在 SQL Editor 执行 `sql/001_create_tables.sql`
3. 在 Storage 创建 bucket：`weight-clinic-files`
4. 创建 GitHub 仓库并上传本项目
5. 在 Streamlit Community Cloud 创建 app，入口文件填写 `app.py`
6. 在 Secrets 中填写 `.streamlit/secrets.toml.example` 中的内容
7. Deploy

## 本地测试

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

示例账号：admin  
示例密码：admin123

正式使用前必须修改 app_secret 和 password_hash。

## 医学边界

本系统用于减重门诊随访记录、趋势展示与报告生成；不用于自动诊断，不用于自动开药。体成分相关指标为公式估算值，仅用于同一方法下趋势参考。

## 隐私提示

若录入真实患者资料，请先确认所在机构是否允许将患者资料存储至第三方云服务。
