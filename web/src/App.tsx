import { useEffect, useState } from "react";
import { askQuestion, fetchMeta } from "./api";
import { AnswerView } from "./components/AnswerView";
import { ConditionPanel } from "./components/ConditionPanel";
import { SourceCard } from "./components/SourceCard";
import { StageTimeline } from "./components/StageTimeline";
import { EMPTY_CONDITION, toFilterInput } from "./condition";
import { type DemoData, loadDemo } from "./demo";
import type { AskResponse, Meta } from "./types";

const DEMO = import.meta.env.MODE === "demo";
const REPO_URL = "https://github.com/ksunnyoo/grant-finder-rag";

const EXAMPLES = [
	"서울 예비창업자가 신청할 수 있는 사업 알려줘",
	"아산 투자유치 프로그램 신청 방법이 뭐야?",
	"다음 달 마감되는 경기 지역 사업 알려줘",
];

export default function App() {
	const [meta, setMeta] = useState<Meta | null>(null);
	const [demo, setDemo] = useState<DemoData | null>(null);
	const [question, setQuestion] = useState("");
	const [condition, setCondition] = useState(EMPTY_CONDITION);
	const [loading, setLoading] = useState(false);
	const [result, setResult] = useState<AskResponse | null>(null);
	const [error, setError] = useState<string | null>(null);

	useEffect(() => {
		const load = DEMO ? loadDemo().then(setDemo) : fetchMeta().then(setMeta);
		load.catch((e: Error) => setError(e.message));
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

	function pick(q: string) {
		setQuestion(q);
		if (DEMO) {
			setError(null);
			setResult(
				demo?.items.find((item) => item.question === q)?.response ?? null,
			);
		} else {
			void submit(q);
		}
	}

	const asOfDate = demo?.asOfDate ?? meta?.asOfDate;
	const chips = DEMO
		? (demo?.items.map((item) => item.question) ?? [])
		: EXAMPLES;

	return (
		<div className="min-h-screen bg-slate-50 text-slate-900">
			<main className="mx-auto max-w-3xl space-y-4 px-4 py-8">
				<header>
					<h1 className="text-xl font-bold">창업지원사업 공고 검색</h1>
					<p className="mt-1 text-sm text-slate-600">
						K-Startup 공고를 근거로 답하고, 근거가 없으면 답하지 않습니다.
						{asOfDate && ` 기준일 ${asOfDate}`}
					</p>
				</header>

				{DEMO && (
					<div className="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-900">
						<p className="font-medium">저장된 응답을 재생하는 데모입니다.</p>
						<p className="mt-1 text-xs">
							서버를 거치지 않고 미리 저장한 질문 {demo?.items.length ?? 0}개의
							응답을 보여 줍니다. 소요 시간은 저장 당시 로컬 PC에서 측정한
							값입니다
							{demo && ` (저장 ${demo.generatedAt.replace("T", " ")})`}. 직접
							질문하려면{" "}
							<a
								className="underline"
								href={REPO_URL}
								target="_blank"
								rel="noreferrer"
							>
								저장소
							</a>
							의 실행 방법을 따르십시오.
						</p>
					</div>
				)}

				<form
					className="space-y-2"
					onSubmit={(e) => {
						e.preventDefault();
						void submit(question);
					}}
				>
					<textarea
						className="w-full rounded-lg border border-slate-300 bg-white p-3 text-sm disabled:bg-slate-100"
						rows={2}
						maxLength={500}
						disabled={DEMO}
						placeholder={
							DEMO
								? "아래 질문을 눌러 저장된 응답을 확인하십시오"
								: "예: 서울 예비창업자가 신청할 수 있는 사업 알려줘"
						}
						value={question}
						onChange={(e) => setQuestion(e.target.value)}
					/>
					<div className="flex flex-wrap items-center gap-2">
						{!DEMO && (
							<button
								type="submit"
								disabled={loading || !question.trim()}
								className="rounded-md bg-blue-600 px-4 py-1.5 text-sm font-medium text-white disabled:bg-slate-300"
							>
								{loading ? "검색 중…" : "질문하기"}
							</button>
						)}
						{chips.map((ex) => (
							<button
								key={ex}
								type="button"
								disabled={loading}
								onClick={() => pick(ex)}
								className="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50"
							>
								{ex}
							</button>
						))}
					</div>
				</form>

				{!DEMO && (
					<ConditionPanel
						meta={meta}
						value={condition}
						onChange={setCondition}
					/>
				)}

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

				<footer className="space-y-1 border-t border-slate-200 pt-4 text-xs text-slate-500">
					<p>
						답변은 참고용입니다. 신청 자격과 마감일은 반드시 공고 원문에서
						확인하십시오.
					</p>
					<p>
						공고 출처: 창업진흥원 K-Startup 조회서비스(공공데이터포털,
						이용허락범위 제한 없음). 원문은 K-Startup 누리집에서 확인할 수
						있습니다.
					</p>
				</footer>
			</main>
		</div>
	);
}
