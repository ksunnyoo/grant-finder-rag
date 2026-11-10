import type { Session } from "@supabase/supabase-js";
import { type FormEvent, useState } from "react";
import { supabase } from "../supabase";

export function AuthBar({ session }: { session: Session | null }) {
	const [open, setOpen] = useState(false);
	const [email, setEmail] = useState("");
	const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">(
		"idle",
	);
	const [message, setMessage] = useState("");

	if (!supabase) return null;
	const client = supabase;

	async function sendLink(e: FormEvent) {
		e.preventDefault();
		if (!email.trim()) return;
		setStatus("sending");
		const { error } = await client.auth.signInWithOtp({
			email: email.trim(),
			options: {
				emailRedirectTo: `${window.location.origin}${import.meta.env.BASE_URL}`,
			},
		});
		if (error) {
			setStatus("error");
			setMessage(error.message);
			return;
		}
		setStatus("sent");
	}

	if (session) {
		return (
			<div className="flex items-center gap-2 text-xs text-slate-600">
				<span>{session.user.email}</span>
				<button
					type="button"
					onClick={() => void client.auth.signOut()}
					className="rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-100"
				>
					로그아웃
				</button>
			</div>
		);
	}

	return (
		<div className="text-xs text-slate-600">
			{!open ? (
				<button
					type="button"
					onClick={() => setOpen(true)}
					className="rounded border border-slate-300 px-2 py-0.5 hover:bg-slate-100"
				>
					로그인
				</button>
			) : (
				<form onSubmit={sendLink} className="space-y-1">
					<div className="flex gap-1">
						<input
							type="email"
							required
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							placeholder="이메일 주소"
							className="w-44 rounded border border-slate-300 px-2 py-0.5"
						/>
						<button
							type="submit"
							disabled={status === "sending"}
							className="rounded bg-blue-600 px-2 py-0.5 text-white disabled:bg-slate-300"
						>
							링크 받기
						</button>
					</div>
					{status === "sent" && (
						<p>메일로 로그인 링크를 보냈습니다. 메일의 링크를 눌러 주십시오.</p>
					)}
					{status === "error" && <p className="text-red-700">{message}</p>}
					<p className="text-slate-500">
						로그인하지 않아도 모든 기능을 쓸 수 있습니다. 로그인하면 저장함이
						계정에 저장됩니다.
					</p>
				</form>
			)}
		</div>
	);
}
