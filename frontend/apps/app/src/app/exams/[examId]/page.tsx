import * as React from "react";
import { LockKeyhole, LogIn } from "lucide-react";

import { AppShell } from "../../../components/app-shell";
import { TrustedExamWorkspace } from "../../../components/trusted-exam-workspace";
import { appPublicPath } from "../../../lib/paths";
import { getServerAuthSession } from "../../../lib/server-auth";
import { Button, Panel } from "@aioj/ui";

type PageProps = { params: Promise<{ examId: string }> };

export default async function ExamWorkspacePage({ params }: PageProps) {
  const { examId } = await params;
  const { demoMode } = await getServerAuthSession();

  if (demoMode) {
    return (
      <AppShell immersive demoMode>
        <div className="flex h-full items-center justify-center p-6">
          <Panel className="w-full max-w-xl p-8 text-center" tone="strong">
            <LockKeyhole size={36} className="mx-auto text-[var(--warning)]" />
            <h1 className="mt-4 text-2xl font-semibold text-[var(--text-primary)]">正式考试需要登录</h1>
            <p className="mt-3 text-sm leading-7 text-[var(--text-secondary)]">
              测试体验不会创建考试作答记录，也不会采集考试行为。请使用已获得考试资格的正式账号登录。
            </p>
            <a href={appPublicPath("/login")} className="mt-6 inline-flex">
              <Button>
                <LogIn size={15} />
                前往正式登录
              </Button>
            </a>
          </Panel>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell immersive>
      <TrustedExamWorkspace examId={examId} />
    </AppShell>
  );
}
