from app.retrieval.models import RetrievedEvidence


def _dedup_key(item: RetrievedEvidence) -> tuple[str, str, str, str]:
    return (
        item.source_type,
        item.source_id,
        item.title or "",
        item.snippet,
    )


def deduplicate_evidence(items: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
    merged_by_key: dict[tuple[str, str, str, str], RetrievedEvidence] = {}

    for item in items:
        item_key = _dedup_key(item)
        matched_routes = sorted(
            {
                item.route_name,
                *[str(route) for route in item.metadata.get("matched_routes", [])],
            }
        )
        normalized_item = item if matched_routes == [item.route_name] else RetrievedEvidence(
            evidence_id=item.evidence_id,
            route_name=item.route_name,
            source_type=item.source_type,
            source_id=item.source_id,
            title=item.title,
            snippet=item.snippet,
            score=item.score,
            metadata={
                **item.metadata,
                "matched_routes": matched_routes,
            },
        )

        existing = merged_by_key.get(item_key)
        if existing is None:
            merged_by_key[item_key] = normalized_item
            continue

        existing_routes = set(str(route) for route in existing.metadata.get("matched_routes", []))
        if not existing_routes:
            existing_routes = {existing.route_name}
        combined_routes = sorted(existing_routes | set(matched_routes))

        best_item = existing
        if (normalized_item.score or 0.0) > (existing.score or 0.0):
            best_item = normalized_item

        merged_by_key[item_key] = RetrievedEvidence(
            evidence_id=best_item.evidence_id,
            route_name=best_item.route_name,
            source_type=best_item.source_type,
            source_id=best_item.source_id,
            title=best_item.title,
            snippet=best_item.snippet,
            score=max(existing.score or 0.0, normalized_item.score or 0.0),
            metadata={
                **existing.metadata,
                **normalized_item.metadata,
                "matched_routes": combined_routes,
            },
        )

    return list(merged_by_key.values())
