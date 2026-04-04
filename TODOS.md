# TODOS

## 当前优先级

- [ ] 把 FastAPI 后端真实跑起来，验证 `/tasks`、`/tasks/{id}`、`/continue`、`/abort`
- [ ] 接入真实数据文件读取路径，替换当前手填路径方式
- [x] 把 `literature_search.py` 从单一 fallback 升级到 `paper-qa` / OpenAlex / fallback 适配层
- [ ] 接入 LangGraph + Redis Checkpoint 持久化，当前已完成任务仓库 / checkpoint 仓库双后端抽象，以及运行时探测接口

## 工程质量

- [ ] 补后端 API 测试
- [ ] 补前端交互测试（当前前端已暂停）
- [ ] 补端到端中断流测试
- [ ] 把 `scw agent mvp/` 中可复用逻辑迁移进新架构，而不是长期双轨维护
