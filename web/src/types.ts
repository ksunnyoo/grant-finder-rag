export type Source = {
	id: string;
	title: string;
	agency: string | null;
	category: string | null;
	region: string | null;
	endDate: string | null;
	dDay: number | null;
	snippet: string;
	url: string;
	flags: string[];
};

export type AskResponse = {
	answer: string;
	refused: boolean;
	refuseReason: string | null;
	sources: Source[];
	appliedFilters: Record<string, unknown>;
	llmProvider: string | null;
	asOfDate: string;
	stages: Record<string, number>;
	latencyMs: number;
};

export type Meta = {
	asOfDate: string;
	regions: string[];
	targets: string[];
	categories: string[];
	bizAges: string[];
	refuseThreshold: number;
};

export type FilterInput = {
	region?: string[];
	target?: string[];
	category?: string[];
	bizAge?: string[];
	age?: number;
	endFrom?: string;
	endTo?: string;
	includeClosed?: boolean;
};
