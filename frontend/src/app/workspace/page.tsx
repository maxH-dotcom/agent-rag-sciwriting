import Link from "next/link";
import { TaskConsole } from "../../../components/task-console";
import styles from "./page.module.css";

export default function WorkspacePage() {
  return (
    <main className={styles.main}>
      <div className={styles.header}>
        <div className={styles.headerRow}>
          <h1 className={styles.title}>科研工作台</h1>
          <Link href="/settings" className={styles.settingsLink}>
            设置
          </Link>
        </div>
        <p className={styles.subtitle}>
          从这里创建任务，随后依次穿过每个中断点。当前版本已经支持创建、查看、继续、终止任务。
        </p>
      </div>
      <TaskConsole />
    </main>
  );
}
