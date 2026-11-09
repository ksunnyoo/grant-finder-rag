export type EvalMetric = {
	name: string;
	hitAtK: number;
	mrr: number;
	precisionFilter: number;
	precisionDate: number;
	precisionMulti: number;
	medianMs: number;
};

export type EvalSet = {
	id: string;
	title: string;
	description: string;
	evaluated: string;
	hasPrecision: boolean;
	metrics: EvalMetric[];
};

export type E2eRow = {
	qid: string;
	type: string;
	question: string;
	refused: boolean;
	reason: string | null;
	cited: boolean;
	goldInSources: boolean;
	latencyMs: number;
};

export type E2eData = {
	refusalCorrect: number;
	nNoAnswer: number;
	overRefused: number;
	nAnswerable: number;
	cited: number;
	nAnswered: number;
	goldInSources: number;
	nLookup: number;
	medianMs: number;
	rows: E2eRow[];
};

export type EvalData = {
	asOfDate: string;
	generatedAt: string;
	sets: EvalSet[];
	e2e: E2eData;
	limits: string[];
};

export async function loadEval(): Promise<EvalData> {
	const res = await fetch(`${import.meta.env.BASE_URL}demo/eval.json`);
	if (!res.ok) throw new Error("평가 데이터를 불러오지 못했습니다.");
	return res.json() as Promise<EvalData>;
}
