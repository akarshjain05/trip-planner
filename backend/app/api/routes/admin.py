from app.models.audit import AuditLog
from fastapi import HTTPException
import datetime
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.agent import AgentRun
from app.models.user import User
from app.api.deps import get_current_user

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/stats")
async def get_admin_stats(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Audit log
    audit = AuditLog(user_id=current_user.id, action="view_admin_stats")
    db.add(audit)
    await db.commit()

    # Aggregate data
    total_runs = await db.execute(select(func.count(AgentRun.id)))
    total_runs = total_runs.scalar_one()

    totals = await db.execute(select(
        func.sum(AgentRun.input_tokens),
        func.sum(AgentRun.output_tokens),
        func.sum(AgentRun.estimated_cost_usd),
        func.sum(AgentRun.iteration_count),
        func.sum(AgentRun.tool_call_count)
    ))
    t_in, t_out, t_cost, t_iters, t_tools = totals.fetchone()

    # Recent runs
    recent = await db.execute(
        select(AgentRun).order_by(AgentRun.created_at.desc()).limit(50)
    )
    recent_runs = recent.scalars().all()

    return {
        "aggregate": {
            "total_runs": total_runs,
            "total_input_tokens": t_in or 0,
            "total_output_tokens": t_out or 0,
            "total_cost_usd": t_cost or 0.0,
            "total_iterations": t_iters or 0,
            "total_tool_calls": t_tools or 0,
        },
        "recent_runs": [
            {
                "id": str(r.id),
                "trip_id": str(r.trip_id),
                "status": r.status,
                "trigger": r.trigger,
                "iteration_count": r.iteration_count,
                "tool_call_count": r.tool_call_count,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "created_at": r.created_at,
            }
            for r in recent_runs
        ]
    }
