import { NextResponse } from "next/server";
import { getRun } from "../../../../lib/store";
import { getCurrentUser } from "../../../../lib/auth";
import { redis, redisConfigured } from "../../../../lib/redis";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  ctx: { params: Promise<{ id: string }> },
) {
  const user = await getCurrentUser();
  if (!user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await ctx.params;
  const run = await getRun(id);
  if (!run) {
    return NextResponse.json({ error: "Run not found" }, { status: 404 });
  }

  // Scoping check: users can only view their own runs
  if (run.userId && run.userId !== user.id) {
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });
  }

  const { searchParams } = new URL(_request.url);
  const path = searchParams.get("path");

  if (!path) {
    return NextResponse.json({ error: "Missing path parameter" }, { status: 400 });
  }

  if (path === "manifest.json") {
    if (!redisConfigured) {
      // Memory fallback for mock runs
      const mockManifest = {
        run_id: id,
        task_id: run.taskId,
        status: run.status,
        score: run.score,
        verdict: run.verdict,
        logs: run.logs,
      };
      return new NextResponse(JSON.stringify(mockManifest, null, 2), {
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": `attachment; filename="manifest_${id}.json"`,
        },
      });
    }

    const manifestRaw = await redis.get(`sandbench:manifest:${id}`);
    if (!manifestRaw) {
      return NextResponse.json({ error: "Manifest not found" }, { status: 404 });
    }

    return new NextResponse(manifestRaw, {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `attachment; filename="manifest_${id}.json"`,
      },
    });
  }

  if (path === "bundle.json") {
    if (!redisConfigured) {
      const mockBundle = {
        run_id: id,
        bundle_hash: "bndl_mock_hash",
        artifact_hashes: {
          "manifest.json": "mock_hash_1",
          "bundle.json": "mock_hash_2",
        },
      };
      return new NextResponse(JSON.stringify(mockBundle, null, 2), {
        headers: {
          "Content-Type": "application/json",
          "Content-Disposition": `attachment; filename="bundle_${id}.json"`,
        },
      });
    }

    const artifactRaw = await redis.get(`sandbench:artifact:${id}`);
    if (!artifactRaw) {
      return NextResponse.json({ error: "Artifact bundle info not found" }, { status: 404 });
    }

    const data = JSON.parse(artifactRaw);
    const bundleJson = {
      run_id: id,
      bundle_hash: data.bundle_hash,
      artifact_hashes: data.artifact_hashes,
    };

    return new NextResponse(JSON.stringify(bundleJson, null, 2), {
      headers: {
        "Content-Type": "application/json",
        "Content-Disposition": `attachment; filename="bundle_${id}.json"`,
      },
    });
  }

  return NextResponse.json({ error: "Unsupported artifact path" }, { status: 400 });
}
