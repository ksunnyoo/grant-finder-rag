import { STAGE_LABELS } from "../format";

export function StageTimeline({
	stages,
	totalMs,
}: {
	stages: Record<string, number>;
	totalMs: number;
}) {
	const entries = Object.keys(STAGE_LABELS)
		.filter((key) => key in stages)
		.map((key) => ({ key, label: STAGE_LABELS[key], ms: stages[key] }));
	const sum = entries.reduce((acc, e) => acc + e.ms, 0) || 1;
	return (
		<div className="rounded-lg border border-slate-200 bg-white p-4">
			<p className="mb-2 text-xs font-medium text-slate-600">
				단계별 소요 시간 (총 {totalMs}ms)
			</p>
			<ul className="space-y-1.5">
				{entries.map((e) => (
					<li
						key={e.key}
						className="flex items-center gap-2 text-xs text-slate-600"
					>
						<span className="w-16 shrink-0">{e.label}</span>
						<div className="h-2 flex-1 rounded bg-slate-100">
							<div
								className="h-2 rounded bg-blue-500"
								style={{ width: `${Math.max(2, (e.ms / sum) * 100)}%` }}
							/>
						</div>
						<span className="w-14 shrink-0 text-right">{e.ms}ms</span>
					</li>
				))}
			</ul>
		</div>
	);
}
