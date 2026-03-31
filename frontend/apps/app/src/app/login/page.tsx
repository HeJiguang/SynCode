"use client";

import * as React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { setBrowserAccessToken } from "@aioj/api";
import { Button, Input, Panel } from "@aioj/ui";
import { appApiPath, appInternalPath } from "../../lib/paths";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [status, setStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function sendCode() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/send-code"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "楠岃瘉鐮佸彂閫佸け璐ャ€?");
      }

      setStatus("楠岃瘉鐮佸凡鍙戦€侊紝璇锋鏌ラ偖绠便€?");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "楠岃瘉鐮佸彂閫佸け璐ャ€?");
    } finally {
      setLoading(false);
    }
  }

  async function login() {
    setLoading(true);
    setStatus(null);

    try {
      const response = await fetch(appApiPath("/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, code })
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.message ?? "鐧诲綍澶辫触銆?");
      }

      setBrowserAccessToken(payload.token);
      router.push(appInternalPath("/"));
      router.refresh();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "鐧诲綍澶辫触銆?");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen px-4 py-6 md:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-[1400px] gap-4 lg:grid-cols-[1.12fr_0.88fr]">
        <Panel className="hidden p-8 lg:flex lg:flex-col lg:justify-between" tone="accent">
          <div>
            <p className="kicker">SynCode</p>
            <h1 className="mt-3 max-w-xl text-5xl font-semibold leading-tight tracking-[-0.04em]">
              鐧诲綍鐪熷疄鍚庣鐜
            </h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-[var(--text-secondary)]">
              褰撳墠鐧诲綍鐩存帴杩炴帴鍒?`http://localhost:19090`銆傝緭鍏ラ偖绠卞悗鍏堝彂閫侀獙璇佺爜锛屽啀鐢ㄩ偖绠遍獙璇佺爜鐧诲綍銆?
            </p>
          </div>
        </Panel>

        <Panel className="flex items-center justify-center p-6 md:p-10">
          <div className="w-full max-w-[460px]">
            <p className="kicker">Sign In</p>
            <h2 className="mt-3 text-3xl font-semibold">鐧诲綍 SynCode</h2>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              浣跨敤閭楠岃瘉鐮佽繘鍏ュ伐浣滃彴銆傛湭鐧诲綍鏃剁郴缁熶細鎸佺画鎻愮ず褰撳墠姝ｅ湪浣跨敤婕旂ず鏁版嵁銆?
            </p>

            <div className="mt-6 space-y-4">
              <Input placeholder="杈撳叆閭鍦板潃" value={email} onChange={(event) => setEmail(event.target.value)} />

              <div className="grid gap-3 md:grid-cols-[1fr_120px]">
                <Input placeholder="杈撳叆楠岃瘉鐮?" value={code} onChange={(event) => setCode(event.target.value)} />
                <Button disabled={loading || !email} variant="secondary" onClick={sendCode}>
                  鍙戦€侀獙璇佺爜
                </Button>
              </div>

              <Button className="w-full" disabled={loading || !email || !code} size="lg" onClick={login}>
                鐧诲綍
              </Button>

              {status ? <p className="text-sm text-[var(--text-secondary)]">{status}</p> : null}
            </div>
          </div>
        </Panel>
      </div>
    </main>
  );
}
