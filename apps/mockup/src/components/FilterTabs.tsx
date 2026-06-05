import styles from "./FilterTabs.module.css";

export interface TabDef {
  key: string;
  label: string;
  count?: number;
}

export default function FilterTabs({
  tabs,
  active,
  onChange,
}: {
  tabs: TabDef[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className={styles.tabs}>
      {tabs.map((t) => (
        <button
          key={t.key}
          className={`${styles.tab} ${active === t.key ? styles.active : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
          {t.count != null && <span className={styles.count}>{t.count}</span>}
        </button>
      ))}
    </div>
  );
}
