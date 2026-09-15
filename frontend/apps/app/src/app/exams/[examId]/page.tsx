import * as React from "react";
import { AppShell } from "../../../components/app-shell";
import { TrustedExamWorkspace } from "../../../components/trusted-exam-workspace";
import { getServerAuthSession } from "../../../lib/server-auth";

type PageProps = { params: Promise<{ examId: string }> };

export default async function ExamWorkspacePage({ params }: PageProps) {
  const { examId } = await params;
  const { demoMode } = await getServerAuthSession();

  return (
    <AppShell immersive demoMode={demoMode}>
      <TrustedExamWorkspace examId={examId} demoMode={demoMode} />
    </AppShell>
  );
}
