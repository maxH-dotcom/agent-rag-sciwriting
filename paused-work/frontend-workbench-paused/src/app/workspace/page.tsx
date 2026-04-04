import { TaskConsole } from "../../../components/task-console";

export default function WorkspacePage() {
  return (
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "32px 24px" }}>
      <h1 style={{ fontSize: 32 }}>科研工作台</h1>
      <p style={{ color: "#4b5563" }}>
        从这里创建任务，随后依次穿过每个中断点。当前版本已经支持创建、查看、继续、终止任务。
      </p>
      <TaskConsole />
    </main>
  );
}
