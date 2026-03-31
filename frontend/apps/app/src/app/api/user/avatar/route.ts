import { NextResponse } from "next/server";

import { buildAuthHeaders, resolveBackendBaseUrl, type ApiEnvelope, requestJson, unwrapData } from "@aioj/api";

import { getServerAccessToken } from "../../../../lib/server-auth";

type UploadResult = {
  name?: string | null;
  success?: boolean;
};

export async function POST(request: Request) {
  const token = await getServerAccessToken();
  if (!token) {
    return NextResponse.json({ message: "未登录，无法上传头像。" }, { status: 401 });
  }

  const incoming = await request.formData();
  const file = incoming.get("file");
  if (!(file instanceof File)) {
    return NextResponse.json({ message: "请选择需要上传的头像文件。" }, { status: 400 });
  }

  const formData = new FormData();
  formData.append("file", file, file.name);
  const headers = new Headers();
  const authHeader = buildAuthHeaders(token).Authorization;
  if (authHeader) {
    headers.set("Authorization", authHeader);
  }

  const uploadResponse = await fetch(`${resolveBackendBaseUrl()}/friend/file/upload`, {
    method: "POST",
    headers,
    body: formData,
    cache: "no-store"
  });

  const uploadText = await uploadResponse.text();
  if (!uploadResponse.ok) {
    return NextResponse.json({ message: uploadText || "头像上传失败。" }, { status: uploadResponse.status });
  }

  const uploadPayload = JSON.parse(uploadText) as ApiEnvelope<UploadResult>;
  const uploadData = unwrapData(uploadPayload);
  if (!uploadData.name) {
    return NextResponse.json({ message: "头像上传成功，但未返回文件地址。" }, { status: 502 });
  }

  await requestJson<ApiEnvelope<null>>("/friend/user/head-image/update", {
    method: "PUT",
    token,
    body: JSON.stringify({ headImage: uploadData.name })
  }).then(unwrapData);

  return NextResponse.json({ ok: true, headImageKey: uploadData.name });
}
