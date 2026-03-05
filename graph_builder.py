from models import Person
from collections import deque

def assign_call(caller: Person, callee: Person):
    caller.calls.append(callee)
    callee.called_by.append(caller)

def rank_gap_ok(caller: Person, callee: Person, same_platoon: bool = False) -> bool:
    if caller.is_initiator and callee.is_initiator:
        return True
    if (caller.is_initiator or caller.is_pl_appt) and callee.is_initiator:
        return True
    # Within own platoon, all senior ranks (LTA/2LT/1SG + PL-SGT 2SGs) call each other freely
    if same_platoon and caller.is_senior and callee.is_senior:
        return True
    # Caller must outrank or equal callee (using effective_rank_level so plain 2SG == 3SG)
    if caller.effective_rank_level <= callee.effective_rank_level:
        return True
    # Cross-platoon senior ranks: at most 1 rank level upward (by effective level)
    if caller.is_senior and callee.is_senior:
        return (caller.effective_rank_level - callee.effective_rank_level) <= 1
    return False

def platoon_ok(caller: Person, callee: Person) -> bool:
    if caller.platoon == callee.platoon:
        return True
    if caller.is_initiator:
        # Initiators may not call 3SGs outside their own platoon
        if callee.rank.strip().upper() == "3SG" and callee.platoon != caller.platoon:
            return False
        return True
    if caller.is_pl_appt:
        return callee.is_pl_appt or callee.is_initiator
    if caller.is_senior:
        # Senior non-PC/PS ranks may not call troopers cross-platoon
        if callee.rank.strip().upper() in {"CPL", "LCP", "PTE", "CFC"}:
            return False
        return True
    return False

PC_PS_MAX_CROSS_PLATOON_CALLS = 1

def can_assign(caller: Person, callee: Person) -> bool:
    if callee is caller:
        return False
    if callee in caller.calls:
        return False
    # Bidirectional calls are allowed within HQ; elsewhere reverse calls are blocked
    if caller in callee.calls:
        both_hq = caller.platoon.strip().upper() == "HQ" and callee.platoon.strip().upper() == "HQ"
        if not both_hq:
            return False
    if not rank_gap_ok(caller, callee, same_platoon=(caller.platoon == callee.platoon)):
        return False
    if not caller.can_call_more():
        return False
    if not callee.can_be_called_more():
        return False
    if not platoon_ok(caller, callee):
        return False
    # PC/PS are limited to at most PC_PS_MAX_CROSS_PLATOON_CALLS cross-platoon outbound calls
    if caller.is_pl_appt and callee.platoon != caller.platoon:
        cross_plt_count = sum(1 for c in caller.calls if c.platoon != caller.platoon)
        if cross_plt_count >= PC_PS_MAX_CROSS_PLATOON_CALLS:
            return False
    return True

def caller_priority_for_3sg(caller: Person, callee: Person) -> int:
    """
    When the callee is a 3SG, prefer same-platoon 3SG callers over cross-platoon PC/PS.
      0 = same-platoon 3SG caller (highest priority)
      1 = same-platoon PC/PS caller
      2 = cross-platoon PC/PS caller
      3 = everything else
    """
    if callee.rank.strip().upper() != "3SG":
        return 3
    same_plt = caller.platoon == callee.platoon
    if caller.rank.strip().upper() == "3SG" and same_plt:
        return 0
    if caller.is_pl_appt and same_plt:
        return 1
    if caller.is_pl_appt and not same_plt:
        return 2
    return 3

def caller_priority_for_pl(caller: Person, callee: Person) -> int:
    """
    When the callee is a PC/PS, prefer same-platoon PC/PS callers before cross-platoon.
      0 = same-platoon PC/PS caller
      1 = initiator caller
      2 = cross-platoon PC/PS caller
      3 = everything else
    """
    if not callee.is_pl_appt:
        return 3
    same_plt = caller.platoon == callee.platoon
    if caller.is_pl_appt and same_plt:
        return 0
    if caller.is_initiator:
        return 1
    if caller.is_pl_appt and not same_plt:
        return 2
    return 3

def pl_call_priority(caller: Person, callee: Person) -> tuple:
    """
    For PL COMD/SGT callers, ordering priority:
      0 = same-platoon PL COMD/SGT (call first)
      1 = cross-platoon PL COMD/SGT
      2 = same-platoon 3SG (and demoted 2SG)
      3 = everything else
    """
    if not caller.is_pl_appt:
        return (3,)
    same_plt = callee.platoon == caller.platoon
    if callee.is_pl_appt and same_plt:
        return (0,)
    if callee.is_pl_appt and not same_plt:
        return (1,)
    if same_plt and callee.effective_rank_level >= 5:  # 3SG / demoted 2SG
        return (2,)
    return (3,)

def build_graph(people: list[Person]) -> list[str]:
    warnings = []
    available = [p for p in people if p.available]
    initiators = [p for p in available if p.is_initiator]

    if not initiators:
        warnings.append("No available initiators — graph is empty.")
        return warnings

    # ---------------------------------------------------------------
    # Phase 0: Initiators call each other (one-directional).
    # Each initiator calls all other initiators where capacity allows.
    # Reverse calls are not required — each initiator just needs at
    # least one inbound caller from another initiator.
    # ---------------------------------------------------------------
    for caller in initiators:
        for callee in initiators:
            if callee is caller:
                continue
            if can_assign(caller, callee):
                assign_call(caller, callee)

    for p in initiators:
        n = sum(1 for c in p.called_by if c.is_initiator)
        if n < 1:
            warnings.append(
                f"Note: {p.rank} {p.name} (Initiator) has no initiator callers — may be unreachable."
            )

    reached = set(p.name for p in initiators)

    # ---------------------------------------------------------------
    # Phase 1: Initiators fill remaining slots in priority order:
    #   1. Other initiators (already done in Phase 0)
    #   2. PL COMDs and PL SGTs not yet reached (any platoon)
    #   3. Anyone not yet reached in own platoon
    # ---------------------------------------------------------------
    for initiator in initiators:
        if not initiator.can_call_more():
            continue

        # Priority 2: uncalled PL COMDs/SGTs — but reserve 1 slot if own platoon has uncalled members
        plt_uncalled_check = [
            p for p in available
            if p.platoon == initiator.platoon
            and not p.is_initiator
            and p.name not in reached
            and can_assign(initiator, p)
        ]
        reserve = 1 if plt_uncalled_check else 0

        pl_uncalled = [
            p for p in available
            if p.is_pl_appt
            and p.name not in reached
            and can_assign(initiator, p)
        ]
        pl_uncalled.sort(key=lambda p: (len(p.called_by), p.effective_rank_level))
        for callee in pl_uncalled:
            # Stop if only the reserved slot remains
            if initiator.call_limit() - len(initiator.calls) <= reserve:
                break
            assign_call(initiator, callee)
            reached.add(callee.name)

        # Priority 3: uncalled people in own platoon (uses reserved slot + any remaining)
        plt_uncalled = [
            p for p in available
            if p.platoon == initiator.platoon
            and not p.is_initiator
            and p.name not in reached
            and can_assign(initiator, p)
        ]
        plt_uncalled.sort(key=lambda p: (p.effective_rank_level, len(p.called_by)))
        for callee in plt_uncalled:
            if not initiator.can_call_more():
                break
            assign_call(initiator, callee)
            reached.add(callee.name)

    # ---------------------------------------------------------------
    # Phase 2a: PC/PS intra-platoon pre-pass
    # Every PC/PS should be called by their own platoon's PC/PS first.
    # If their same-platoon PC/PS partners are at capacity, boost them by +1
    # before allowing cross-platoon PC/PS to fill that slot.
    # ---------------------------------------------------------------
    pl_appt_people = [p for p in available if p.is_pl_appt]

    for target in pl_appt_people:
        # Find same-platoon PC/PS who can still call this target
        same_plt_pl = [
            p for p in available
            if p.is_pl_appt
            and p.platoon == target.platoon
            and can_assign(p, target)
        ]
        # If none available but there are eligible same-platoon PC/PS at limit, boost them
        if not same_plt_pl:
            boostable = [
                p for p in available
                if p.is_pl_appt
                and p.platoon == target.platoon
                and p is not target
                and target not in p.calls
                and p not in target.calls
                and rank_gap_ok(p, target, same_platoon=True)
                and platoon_ok(p, target)
                and target.can_be_called_more()
            ]
            for p in boostable:
                p._call_limit_boost = getattr(p, '_call_limit_boost', 0) + 1
            same_plt_pl = [
                p for p in available
                if p.is_pl_appt
                and p.platoon == target.platoon
                and can_assign(p, target)
            ]
            # Undo boosts that didn't help
            for p in boostable:
                if p not in same_plt_pl:
                    p._call_limit_boost = max(0, getattr(p, '_call_limit_boost', 0) - 1)
            if same_plt_pl:
                warnings.append(
                    f"Note: boosted same-platoon PC/PS call limit in Plt {target.platoon} "
                    f"to call {target.rank} {target.name} before cross-platoon PC/PS."
                )
        for caller in same_plt_pl:
            if not can_assign(caller, target):
                continue
            assign_call(caller, target)
            reached.add(target.name)

        # Force-add a same-platoon PC/PS caller even if target is already at 3 callers,
        # as long as no same-platoon PC/PS has called them yet.
        has_same_plt_pl_caller = any(
            c.is_pl_appt and c.platoon == target.platoon for c in target.called_by
        )
        if not has_same_plt_pl_caller:
            force_candidates = [
                p for p in available
                if p.is_pl_appt
                and p.platoon == target.platoon
                and p is not target
                and target not in p.calls
                and p not in target.calls
                and rank_gap_ok(p, target, same_platoon=True)
                and platoon_ok(p, target)
            ]
            if force_candidates:
                force_candidates.sort(key=lambda p: len(p.calls))
                best = force_candidates[0]
                if not best.can_call_more():
                    best._call_limit_boost = getattr(best, '_call_limit_boost', 0) + 1
                assign_call(best, target)
                reached.add(target.name)
                warnings.append(
                    f"Note: force-added same-platoon PC/PS caller ({best.rank} {best.name}) "
                    f"for {target.rank} {target.name} (Plt {target.platoon})."
                )

    # ---------------------------------------------------------------
    # Phase 2b: PC/PS downward pre-pass
    # Before the main saturation fills everyone up, each PC/PS must claim
    # at least one call slot into their own platoon's non-PC/PS members
    # (senior ranks and 3SGs first, then troopers).
    # This prevents lateral 3SG chains from filling all inbound slots
    # before the PC/PS get a turn, which would orphan the platoon from
    # its own leadership.
    # ---------------------------------------------------------------
    for caller in sorted(pl_appt_people, key=lambda p: (p.platoon, p.effective_rank_level)):
        # Count how many same-platoon non-PC/PS calls this PC/PS already has
        same_plt_non_pl_calls = [
            c for c in caller.calls
            if c.platoon == caller.platoon and not c.is_pl_appt and not c.is_initiator
        ]
        if same_plt_non_pl_calls:
            continue  # already has at least one downward same-platoon call

        # Find eligible same-platoon non-PC/PS callees, sorted senior-first
        candidates = [
            p for p in available
            if p.platoon == caller.platoon
            and not p.is_pl_appt
            and not p.is_initiator
            and can_assign(caller, p)
        ]
        candidates.sort(key=lambda p: (p.effective_rank_level, len(p.called_by)))
        if candidates:
            assign_call(caller, candidates[0])
            reached.add(candidates[0].name)

    # ---------------------------------------------------------------
    # Phase 2: Top-down saturation — process callees senior-first
    # For each person, find callers with capacity, respecting all rules.
    # Caller priority:
    #   - For 3SG targets: same-platoon 3SG > same-platoon PC/PS > cross-platoon PC/PS
    #   - For PC/PS targets: same-platoon PC/PS > initiator > cross-platoon PC/PS
    #   - PL COMD/SGT callers follow: same-plt PL -> cross-plt PL -> 3SGs
    # 3SGs prioritise calling fellow 3SGs first; trooper coverage follows with remaining slots.
    # ---------------------------------------------------------------
    TROOPER_RANKS = {"CPL", "LCP", "PTE", "CFC"}

    ordered_callees = sorted(
        available,
        key=lambda p: (p.effective_rank_level, p.platoon, p.name)
    )

    for target in ordered_callees:
        while len(target.called_by) < 2 or (target.is_initiator and len(target.called_by) < 1):
            callers = [p for p in available if can_assign(p, target)]
            if not callers:
                break
            # Sort callers: apply target-specific priority first, then capacity, then rank
            callers.sort(key=lambda p: (
                caller_priority_for_3sg(p, target),  # 3SG targets: same-plt 3SG first
                caller_priority_for_pl(p, target),   # PC/PS targets: same-plt PC/PS first
                -(p.call_limit() - len(p.calls)),    # most capacity first
                pl_call_priority(p, target),          # PL callers respect their own priority
                p.effective_rank_level                # higher rank preferred
            ))
            best = callers[0]
            assign_call(best, target)
            reached.add(target.name)

    # ---------------------------------------------------------------
    # Phase 3: Coverage rescue — anyone still unreached
    # If no one can reach an orphan due to call limits, temporarily raise
    # the limit by 1 for anyone in their platoon who could otherwise call them.
    # ---------------------------------------------------------------
    unreached = [p for p in available if p.name not in reached]
    for orphan in unreached:
        candidates = [p for p in available if can_assign(p, orphan)]
        if not candidates:
            # Try boosting same-platoon callers by +1 slot
            boosted = [
                p for p in available
                if p.platoon == orphan.platoon
                and p is not orphan
                and not p.is_initiator   # initiators use their own limit rules
                and orphan not in p.calls
                and p not in orphan.calls
                and rank_gap_ok(p, orphan, same_platoon=True)
                and platoon_ok(p, orphan)
                and orphan.can_be_called_more()
            ]
            for p in boosted:
                p._call_limit_boost = getattr(p, '_call_limit_boost', 0) + 1
            candidates = [p for p in available if can_assign(p, orphan)]
            # Undo boosts for those who still can't reach orphan
            for p in boosted:
                if p not in candidates:
                    p._call_limit_boost = max(0, getattr(p, '_call_limit_boost', 0) - 1)
            if candidates:
                warnings.append(
                    f"Note: boosted call limit for same-platoon callers to reach "
                    f"{orphan.rank} {orphan.name} (Plt {orphan.platoon})."
                )
        if candidates:
            candidates.sort(key=lambda p: (len(p.calls), p.effective_rank_level))
            assign_call(candidates[0], orphan)
            reached.add(orphan.name)
        else:
            warnings.append(
                f"WARNING: {orphan.rank} {orphan.name} (Plt {orphan.platoon}) unreachable."
            )

    # ---------------------------------------------------------------
    # Phase 4: Final top-up passes
    # ---------------------------------------------------------------
    for _pass in range(3):
        targets = sorted(
            [p for p in available if len(p.called_by) < 2 and not p.is_initiator],
            key=lambda p: (len(p.called_by), p.effective_rank_level)
        )
        if not targets:
            break
        changed = False
        for target in targets:
            extra = [p for p in available if can_assign(p, target)]
            extra.sort(key=lambda p: (len(p.calls), p.effective_rank_level))
            for caller in extra:
                if len(target.called_by) >= 2:
                    break
                assign_call(caller, target)
                changed = True
        if not changed:
            break

    # ---------------------------------------------------------------
    # Phase 5: Best-effort 3SG caller for every trooper (below 3SG).
    # 3SG-to-3SG coverage is the priority; troopers are covered with
    # whatever capacity remains. 3SGs may be boosted up to MAX_3SG_CALL_LIMIT
    # (defined in models.py) for both 3SG peers and troopers.
    # If no same-platoon 3SG caller is available for a trooper, log a note
    # (not a warning) — this is an accepted outcome.
    # ---------------------------------------------------------------
    troopers_without_3sg = [
        p for p in available
        if p.rank.strip().upper() in TROOPER_RANKS
        and not any(c.rank.strip().upper() == "3SG" for c in p.called_by)
    ]

    def can_assign_3sg_force(caller: Person, callee: Person) -> bool:
        """Like can_assign but ignores callee's called_by cap — used only in Phase 5."""
        if callee is caller:
            return False
        if callee in caller.calls:
            return False
        if not rank_gap_ok(caller, callee, same_platoon=(caller.platoon == callee.platoon)):
            return False
        if not platoon_ok(caller, callee):
            return False
        return True  # callee cap intentionally bypassed

    for trooper in troopers_without_3sg:
        # First try normal assignment (3SG still has capacity within max limit)
        sg_candidates = [
            p for p in available
            if p.rank.strip().upper() == "3SG"
            and p.platoon == trooper.platoon
            and can_assign(p, trooper)
        ]

        if not sg_candidates:
            # Try boosting a same-platoon 3SG by +1, up to MAX_3SG_CALL_LIMIT
            eligible_sgs = [
                p for p in available
                if p.rank.strip().upper() == "3SG"
                and p.platoon == trooper.platoon
                and can_assign_3sg_force(p, trooper)
                and p.call_limit() < 5  # only boost if not already at max
            ]
            if eligible_sgs:
                eligible_sgs.sort(key=lambda p: len(p.calls))
                best_sg = eligible_sgs[0]
                best_sg._call_limit_boost = getattr(best_sg, '_call_limit_boost', 0) + 1
                sg_candidates = [best_sg] if can_assign(best_sg, trooper) else []
                if sg_candidates:
                    warnings.append(
                        f"Note: boosted 3SG call limit ({best_sg.rank} {best_sg.name}) "
                        f"to cover {trooper.rank} {trooper.name} (Plt {trooper.platoon})."
                    )

        if not sg_candidates:
            # Force-assign: trooper already at 3 callers but none are 3SG — allow 4th callee slot
            # Only use 3SGs that still have capacity (no further boost here)
            eligible_sgs = [
                p for p in available
                if p.rank.strip().upper() == "3SG"
                and p.platoon == trooper.platoon
                and can_assign_3sg_force(p, trooper)
                and p.can_call_more()
            ]
            if eligible_sgs:
                eligible_sgs.sort(key=lambda p: len(p.calls))
                assign_call(eligible_sgs[0], trooper)
                warnings.append(
                    f"Note: force-added 4th caller ({eligible_sgs[0].rank} {eligible_sgs[0].name}) "
                    f"to {trooper.rank} {trooper.name} (Plt {trooper.platoon}) to satisfy 3SG requirement."
                )
                continue

            # No same-platoon 3SG available — accepted outcome, log as note only
            warnings.append(
                f"Note: {trooper.rank} {trooper.name} (Plt {trooper.platoon}) "
                f"has no available same-platoon 3SG caller — trooper coverage incomplete."
            )
        else:
            sg_candidates.sort(key=lambda p: (len(p.calls), p.name))
            assign_call(sg_candidates[0], trooper)

    # ---------------------------------------------------------------
    # Phase 5b: PC/PS and 3SG same-platoon caller enforcement
    # If a PC/PS or 3SG has a cross-platoon PC/PS caller but no same-platoon
    # PC/PS (or 3SG for 3SG targets) caller, swap one cross-platoon caller out
    # for a same-platoon one. If the same-platoon candidate is at capacity,
    # boost their limit by +1.
    # ---------------------------------------------------------------
    def enforce_same_platoon_caller(targets, get_preferred_callers, get_unwanted_callers):
        for target in targets:
            has_preferred = any(get_preferred_callers(c, target) for c in target.called_by)
            if has_preferred:
                continue
            unwanted = [c for c in target.called_by if get_unwanted_callers(c, target)]
            if not unwanted:
                continue
            # Find an eligible same-platoon preferred caller not already assigned
            candidates = [
                p for p in available
                if get_preferred_callers(p, target)
                and p is not target
                and target not in p.calls
                and p not in target.called_by
                and rank_gap_ok(p, target, same_platoon=(p.platoon == target.platoon))
                and platoon_ok(p, target)
            ]
            if not candidates:
                continue
            candidates.sort(key=lambda p: len(p.calls))
            best = candidates[0]
            # Boost caller if at limit
            if not best.can_call_more():
                best._call_limit_boost = getattr(best, '_call_limit_boost', 0) + 1
            # Remove one unwanted caller (least loaded one first)
            unwanted.sort(key=lambda p: len(p.calls))
            swap_out = unwanted[0]
            swap_out.calls.remove(target)
            target.called_by.remove(swap_out)
            warnings.append(
                f"Note: replaced cross-platoon caller {swap_out.rank} {swap_out.name} "
                f"with same-platoon {best.rank} {best.name} for {target.rank} {target.name} "
                f"(Plt {target.platoon})."
            )
            assign_call(best, target)

    # 3SG targets: prefer same-platoon 3SG callers over cross-platoon PC/PS
    three_sg_targets = [p for p in available if p.rank.strip().upper() == "3SG"]
    enforce_same_platoon_caller(
        three_sg_targets,
        get_preferred_callers=lambda c, t: c.rank.strip().upper() == "3SG" and c.platoon == t.platoon,
        get_unwanted_callers=lambda c, t: c.is_pl_appt and c.platoon != t.platoon,
    )

    # PC/PS targets: prefer same-platoon PC/PS callers over cross-platoon PC/PS
    pl_targets = [p for p in available if p.is_pl_appt]
    enforce_same_platoon_caller(
        pl_targets,
        get_preferred_callers=lambda c, t: c.is_pl_appt and c.platoon == t.platoon,
        get_unwanted_callers=lambda c, t: c.is_pl_appt and c.platoon != t.platoon,
    )

    for p in available:
        if (not p.is_initiator and len(p.called_by) < 2):
            warnings.append(
                f"Note: {p.rank} {p.name} (Plt {p.platoon}) has only "
                f"{len(p.called_by)}/3 callers — not enough valid callers available."
            )

    under3 = sum(1 for p in available if not p.is_initiator and len(p.called_by) < 2)
    warnings.append(
        f"Coverage: {len(reached)}/{len(available)} reachable. "
        f"Personnel with <3 callers: {under3}/{len(available)}."
    )
    return warnings