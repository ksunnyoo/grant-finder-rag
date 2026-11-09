import { useEffect, useState } from "react";
import { askQuestion, fetchMeta } from "./api";
import { AnswerView } from "./components/AnswerView";
import { ConditionPanel } from "./components/ConditionPanel";
import { SourceCard } from "./components/SourceCard";
import { StageTimeline } from "./components/StageTimeline";
import { EMPTY_CONDITION, toFilterInput } from "./condition";
import type { AskResponse, Meta } from "./types";

const EXAMPLES = [
	"서울 예비창업자가 신청할 수 있는 사업 알려줘",
	"아산 투자유치 프로그램 신청 방법이 뭐야?",
	"다음 달 마감되는 경기 지역 사업 알려줘",
];

export default function App() {
	const [meta, setMeta] = useState<Meta | null>(null);
	const [question, setQuestion] = useState("");
	const [condition, setCondition] = useState(EMPTY_CONDITION);
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState<AskResponse | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		fetchMeta()
			.then(setMeta)
			.catch((e: Error) => setError(e.message));
	}, []);

	async function submit(text: string) {
		const q = text.trim();
		if (!q || loading) return;
		setLoading(true);
		setError(null);
		try {
			setResult(await askQuestion(q, toFilterInput(condition)));
		} catch (e) {
			setResult(null);
			setError(
				e instanceof Error ? e.message : "알 수 없는 오류가 발생했습니다.",
			);
		} finally {
			setLoading(false);
		}
	}

	return (
		<div className="min-h-screen bg-slate-50 text-slate-900">
			<main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
				<header>
					<h1 className="text-xl font-bold">창업지원사업 공고 검색</h1>
					<p className="mt-1 text-sm text-slate-600">
						K-Startup 공고를 근거로 답하고, 근거가 없으면 답하지 않습니다.
						{meta && ` 기준일 ${meta.asOfDate}`}
					</p>
				</header>

				<form
					className="space-y-2"
					onSubmit={(e) => {
						e.preventDefault();
						void submit(question);
					}}
				>
					<textarea
						className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm"
						rows={2}
						maxLength={500}
						placeholder="예: 서울 예비창업자가 신청할 수 있는 사업 알려줘"
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
					/>
					<div className="flex flex-wrap items-center gap-2">
						<button
							type="submit"
							disabled={loading || !question.trim()}
							className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white disabled:bg-slate-300"
						>
							{loading ? "검색 중…" : "질문하기"}
						</button>
						{EXAMPLES.map((ex) => (
							<button
								key={ex}
								type="button"
								disabled={loading}
								onClick={() => {
									setQuestion(ex);
									void submit(ex);
								}}
								className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50"
							>
								{ex}
							</button>
						))}
					</div>
				</form>

				<ConditionPanel meta={meta} value={condition} onChange={setCondition} />

				{loading && (
					<p className="text-sm text-slate-500">
						검색하고 답변을 만드는 중입니다. 첫 질문은 모델을 불러오느라 더 걸릴
						수 있습니다.
					</p>
				)}
				{error && (
					<div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
						{error}
					</div>
				)}

				{result && !loading && (
					<>
						<AnswerView result={result} />
						{result.sources.length > 0 && (
							<section className="space-y-2">
								<h2 className="text-sm font-semibold text-slate-700">
									근거 공고 {result.sources.length}건
								</h2>
								{result.sources.map((s) => (
									<SourceCard key={s.id} source={s} />
								))}
							</section>
						)}
						<StageTimeline stages={result.stages} totalMs={result.latencyMs} />
					</>
				)}

				<footer className="border-t border-slate-200 pt-4 text-xs text-slate-500">
					답변은 참고용입니다. 신청 자격과 마감일은 반드시 공고 원문에서
					확인하십시오.
				</footer>
			</main>
		</div>
	);
}
