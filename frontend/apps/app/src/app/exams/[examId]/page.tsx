import * as React from "react";

import { AppShell } from "../../../components/app-shell";
import { TrustedExamWorkspace } from "../../../components/trusted-exam-workspace";

type PageProps = { params: Promise<{ examId: string }> };

export default async function ExamWorkspacePage({ params }: PageProps) {
  const { examId } = await params;
  return (
    <AppShell immersive>
      <TrustedExamWorkspace examId={examId} />
    </AppShell>
  );
}
