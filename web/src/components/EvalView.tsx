import { useEffect, useState } from "react";
import {
	type EvalData,
	type EvalMetric,
	type EvalSet,
	loadEval,
} from "../eval";

const EVAL_DOC_URL =
	"https://github.com/ksunnyoo/grant-finder-rag/blob/main/docs/EVALUATION.md";
const fmt = (v: number) => v.toFixed(2);

function MetricTable({ set }: { set: EvalSet }) {
	const top = (pick: (m: EvalMetric) => number) =>
		Math.max(...set.metrics.map(pick));
	const bestHit = top((m) => m.hitAtK);
	const bestMrr = top((m) => m.mrr);
	const num = (value: number, best?: number) => (
		<td
			className={`px-2 py-1.5 text-right tabular-nums ${value === best ? "font-semibold text-blue-700" : ""}`}
		>
			{fmt(value)}
		</td>
	);
	return (
		<div className="overflow-x-auto">
			<table className="w-full text-xs">
				<thead>
					<tr className="border-b border-slate-200 text-left text-slate-500">
						<th className="px-2 py-1.5 font-medium">구성</th>
						<th className="px-2 py-1.5 text-right font-medium">Hit@5</th>
						<th className="px-2 py-1.5 text-right font-medium">MRR</th>
						{set.hasPrecision && (
							<>
								<th className="px-2 py-1.5 text-right font-medium">
									조건 정밀도
								</th>
								<th className="px-2 py-1.5 text-right font-medium">날짜</th>
								<th className="px-2 py-1.5 text-right font-medium">복합</th>
							</>
						)}
						<th className="px-2 py-1.5 text-right font-medium">
							중앙 지연(ms)
						</th>
					</tr>
				</thead>
				<tbody>
					{set.metrics.map((m) => (
						<tr key={m.name} className="border-b border-slate-100">
							<td className="px-2 py-1.5 text-slate-800">{m.name}</td>
							{num(m.hitAtK, bestHit)}
							{num(m.mrr, bestMrr)}
							{set.hasPrecision && (
								<>
									{num(m.precisionFilter)}
									{num(m.precisionDate)}
									{num(m.precisionMulti)}
								</>
							)}
							<td className="px-2 py-1.5 text-right tabular-nums">
								{m.medianMs.toLocaleString()}
							</td>
						</tr>
					))}
				</tbody>
			</table>
		</div>
	);
}

function Tile(props: { label: string; value: string; note: string }) {
	return (
		<div className="rounded-lg border border-slate-200 bg-white p-3">
			<p className="text-xs text-slate-500">{props.label}</p>
			<p className="mt-1 text-xl font-semibold tabular-nums text-slate-900">
				{props.value}
			</p>
			<p className="mt-1 text-xs text-slate-500">{props.note}</p>
		</div>
	);
}

export function EvalView() {
	const [data, setData] = useState<EvalData | null>(null);
	const [error, setError] = useState<string | null>(null);
	const [active, setActive] = useState("easy");

	useEffect(() => {
		loadEval()
			.then(setData)
			.catch((e: Error) => setError(e.message));
	}, []);

	if (error) {
		return (
			<div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
				{error}
			</div>
		);
	}
	if (!data) return <p className="text-sm text-slate-500">불러오는 중…</p>;

	const set = data.sets.find((s) => s.id === active) ?? data.sets[0];
	const e2e = data.e2e;
	const overRefusedRows = e2e.rows.filter(
		(r) => r.type !== "no_answer" && r.refused,
	);

	return (
		<div className="space-y-6">
			<section className="space-y-3">
				<h2 className="text-sm font-semibold text-slate-700">
					검색 구성 비교 (LLM 없음, 상위 5개)
				</h2>
				<div className="flex flex-wrap gap-1.5">
					{data.sets.map((s) => (
						<button
							key={s.id}
							type="button"
							onClick={() => setActive(s.id)}
							className={`rounded-full border px-3 py-1 text-xs ${
								s.id === set.id
									? "border-blue-600 bg-blue-600 text-white"
									: "border-slate-300 bg-white text-slate-700 hover:bg-slate-100"
							}`}
						>
							{s.title}
						</button>
					))}
				</div>
				<p className="text-xs text-slate-600">
					{set.description}{" "}
					<span className="text-slate-500">({set.evaluated})</span>
				</p>
				<div className="rounded-lg border border-slate-200 bg-white p-2">
					<MetricTable set={set} />
				</div>
				<p className="text-xs text-slate-500">
					파란색은 해당 열의 최고값입니다. Hit@5는 정답이 상위 5개 안에 있는
					비율, MRR은 정답 순위의 역수 평균입니다. 구성 이름에 필터가 없으면
					마감된 공고까지 검색합니다.
				</p>
			</section>

			<section className="space-y-3">
				<h2 className="text-sm font-semibold text-slate-700">
					답변 생성 (LLM 사용, {e2e.rows.length}문항 표본)
				</h2>
				<div className="grid gap-2 sm:grid-cols-2">
					<Tile
						label="범위 밖 질문 거절"
						value={`${e2e.refusalCorrect}/${e2e.nNoAnswer}`}
						note="답이 없는 질문을 거절한 수"
					/>
					<Tile
						label="오거절"
						value={`${e2e.overRefused}/${e2e.nAnswerable}`}
						note="답할 수 있는 질문을 거절한 수 (적을수록 좋음)"
					/>
					<Tile
						label="출처가 붙은 답변"
						value={`${e2e.cited}/${e2e.nAnswered}`}
						note="형식만 확인하며 내용의 정확성은 측정하지 않음"
					/>
					<Tile
						label="정답 공고가 출처에 포함"
						value={`${e2e.goldInSources}/${e2e.nLookup}`}
						note="제목 기반 질문 기준"
					/>
				</div>
				{overRefusedRows.length > 0 && (
					<div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
						<p className="font-medium">오거절된 질문</p>
						<ul className="mt-1 list-inside list-disc">
							{overRefusedRows.map((r) => (
								<li key={r.qid}>
									{r.question} ({r.reason})
								</li>
							))}
						</ul>
					</div>
				)}
				<p className="text-xs text-slate-500">
					답변 생성 중앙 응답 시간 {e2e.medianMs.toLocaleString()}ms (무료
					한도의 Gemini 사용).
				</p>
			</section>

			<section className="rounded-lg border border-slate-200 bg-white p-4">
				<h2 className="text-sm font-semibold text-slate-700">해석의 한계</h2>
				<ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-600">
					{data.limits.map((l) => (
						<li key={l}>{l}</li>
					))}
				</ul>
				<a
					href={EVAL_DOC_URL}
					target="_blank"
					rel="noreferrer"
					className="mt-3 inline-block text-xs font-medium text-blue-700 hover:underline"
				>
					측정 조건과 전체 기록 보기 ↗
				</a>
			</section>
		</div>
	);
}
