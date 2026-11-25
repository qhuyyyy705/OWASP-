from urllib.parse import urlsplit
from sqlalchemy.orm import Session
from app.models import Project

def check_scope(db: Session, project_id: int, url: str) -> tuple[bool, str]:
    try:
        candidate = urlsplit(url)
        if candidate.scheme not in {"http", "https"} or not candidate.hostname or candidate.username or candidate.password:
            return False, "URL must use http(s) and contain no embedded credentials"
        candidate_port = candidate.port or (443 if candidate.scheme == "https" else 80)
    except ValueError:
        return False, "Invalid URL"
    project = db.get(Project, project_id)
    if project is None:
        return False, "Project not found"
    for target in project.targets:
        root = urlsplit(target.origin)
        root_port = root.port or (443 if root.scheme == "https" else 80)
        if (candidate.scheme, candidate.hostname.lower(), candidate_port) == (root.scheme, root.hostname.lower(), root_port):
            return True, "URL matches a configured target origin"
    return False, "URL is outside configured target origins"
