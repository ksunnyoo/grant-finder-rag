import { type Condition, conditionError } from "../condition";
import type { Meta } from "../types";

type Props = {
	meta: Meta | null;
	value: Condition;
	onChange: (next: Condition) => void;
	note?: string;
	hideClosed?: boolean;
};

const SELECT_CLASS =
	"w-full rounded-md border border-slate-300 bg-white px-2 py-1.5 text-sm text-slate-800";

function Select(props: {
	label: string;
	value: string;
	options: string[];
	onChange: (v: string) => void;
}) {
	return (
		<label className="block text-xs font-medium text-slate-600">
			{props.label}
			<select
				className={`${SELECT_CLASS} mt-1`}
				value={props.value}
				onChange={(e) => props.onChange(e.target.value)}
			>
				<option value="">전체</option>
				{props.options.map((o) => (
					<option key={o} value={o}>
						{o}
					</option>
				))}
			</select>
		</label>
	);
}

function Field(props: {
	label: string;
	type: "number" | "date";
	value: string;
	min?: number;
	max?: number;
	onChange: (v: string) => void;
}) {
	return (
		<label className="block text-xs font-medium text-slate-600">
			{props.label}
			<input
				type={props.type}
				className={`${SELECT_CLASS} mt-1`}
				value={props.value}
				min={props.min}
				max={props.max}
				onChange={(e) => props.onChange(e.target.value)}
			/>
		</label>
	);
}

export function ConditionPanel({
	meta,
	value,
	onChange,
	note,
	hideClosed = false,
}: Props) {
	const error = conditionError(value);
	return (
		<div className="rounded-lg border border-slate-200 bg-white p-4">
			<p className="mb-3 text-xs text-slate-500">
				{note ??
					"조건을 직접 고르면 질문에서 추출한 조건보다 우선합니다. 지역, 업력, 마감 시기는 질문에 적어도 자동으로 인식합니다."}
			</p>
			<div className="grid gap-3 sm:grid-cols-3">
				<Select
					label="지역"
					value={value.region}
					options={meta?.regions ?? []}
					onChange={(region) => onChange({ ...value, region })}
				/>
				<Select
					label="대상"
					value={value.target}
					options={meta?.targets ?? []}
					onChange={(target) => onChange({ ...value, target })}
				/>
				<Select
					label="분야"
					value={value.category}
					options={meta?.categories ?? []}
					onChange={(category) => onChange({ ...value, category })}
				/>
			</div>
			<div className="mt-3 grid gap-3 sm:grid-cols-4">
				<Select
					label="업력"
					value={value.bizAge}
					options={meta?.bizAges ?? []}
					onChange={(bizAge) => onChange({ ...value, bizAge })}
				/>
				<Field
					label="연령(만 나이)"
					type="number"
					min={0}
					max={120}
					value={value.age}
					onChange={(age) => onChange({ ...value, age })}
				/>
				<Field
					label="마감 시작일"
					type="date"
					value={value.endFrom}
					onChange={(endFrom) => onChange({ ...value, endFrom })}
				/>
				<Field
					label="마감 종료일"
					type="date"
					value={value.endTo}
					onChange={(endTo) => onChange({ ...value, endTo })}
				/>
			</div>
			{error && (
				<p role="alert" className="mt-2 text-xs text-red-700">
					{error}
				</p>
			)}
			{!hideClosed && (
				<label className="mt-3 flex items-center gap-2 text-sm text-slate-700">
					<input
						type="checkbox"
						checked={value.includeClosed}
						onChange={(e) =>
							onChange({ ...value, includeClosed: e.target.checked })
						}
					/>
					마감된 공고도 포함
				</label>
			)}
		</div>
	);
}
