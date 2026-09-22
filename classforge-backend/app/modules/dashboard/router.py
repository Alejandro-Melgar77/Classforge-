from fastapi import APIRouter, Depends
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.schemas import StandardResponse
from app.modules.teams.repository import TeamRepository
from app.modules.projects.repository import ProjectRepository
from bson import ObjectId

router = APIRouter()

@router.get("/stats", response_model=StandardResponse)
async def get_dashboard_stats(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    user_id = str(current_user["_id"])
    role = current_user.get("role")
    
    team_repo = TeamRepository(db)
    project_repo = ProjectRepository(db)
    user_repo = db["users"] # direct access for stats
    
    # Base queries depending on role
    team_query = {"is_deleted": False}
    project_query = {"is_deleted": False}
    
    if role == "scrum_master":
        team_query["scrum_master_id"] = ObjectId(user_id)
        teams = await team_repo.collection.find(team_query).to_list(length=1000)
        team_ids = [t["_id"] for t in teams]
        project_query["$or"] = [{"team_id": {"$in": team_ids}}, {"owner_id": ObjectId(user_id)}]
    elif role == "dev":
        team_query["member_ids"] = ObjectId(user_id)
        teams = await team_repo.collection.find(team_query).to_list(length=1000)
        team_ids = [t["_id"] for t in teams]
        project_query["$or"] = [{"team_id": {"$in": team_ids}}, {"owner_id": ObjectId(user_id)}]
    
    # Calculate stats
    total_projects = await project_repo.collection.count_documents(project_query)
    
    active_query = {**project_query, "status": "in_progress"}
    active_projects = await project_repo.collection.count_documents(active_query)
    
    completed_query = {**project_query, "status": "completed"}
    completed_projects = await project_repo.collection.count_documents(completed_query)
    
    total_teams = await team_repo.collection.count_documents(team_query)
    
    # For total_members, this could be users in teams or total users for admin
    if role == "admin":
        total_members = await user_repo.count_documents({"is_deleted": False})
    else:
        # distinct members in user's teams
        teams = await team_repo.collection.find(team_query).to_list(length=1000)
        members = set()
        for t in teams:
            for m in t.get("member_ids", []):
                members.add(str(m))
        total_members = len(members)
        
    # Projects by status
    pipeline = [
        {"$match": project_query},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    status_counts = await project_repo.collection.aggregate(pipeline).to_list(length=None)
    projects_by_status = {
        "in_progress": 0, "completed": 0, "review": 0, "archived": 0
    }
    for item in status_counts:
        status = item["_id"]
        if status in projects_by_status:
            projects_by_status[status] = item["count"]
            
    # Recent activity
    activity_query = {}
    if role != "admin":
        activity_query["user_id"] = ObjectId(user_id)
        
    recent_activity = await db["audit_logs"].find(activity_query).sort("created_at", -1).limit(10).to_list(length=10)
    
    # Format activity
    formatted_activity = []
    for log in recent_activity:
        formatted_activity.append({
            "action": log.get("action"),
            "user_id": str(log.get("user_id")),
            "details": log.get("details"),
            "timestamp": log.get("timestamp")
        })
        
    # My projects and teams (limit 5 for dashboard)
    my_projects = await project_repo.collection.find(project_query).sort("created_at", -1).limit(5).to_list(length=5)
    my_teams = await team_repo.collection.find(team_query).sort("created_at", -1).limit(5).to_list(length=5)
    
    data = {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_teams": total_teams,
        "total_members": total_members,
        "recent_activity": formatted_activity,
        "projects_by_status": projects_by_status,
        "my_teams": [{
            "id": str(t["_id"]),
            "name": t["name"],
            "avatar_color": t.get("avatar_color", "#2D6BE4")
        } for t in my_teams],
        "recent_projects": [{
            "id": str(p["_id"]),
            "name": p["name"],
            "status": p["status"],
            "team_id": str(p["team_id"]) if p.get("team_id") else None,
            "updated_at": p.get("updated_at").isoformat() if p.get("updated_at") else None
        } for p in my_projects]
    }
    
    return StandardResponse(success=True, message="Dashboard stats retrieved", data=data)
