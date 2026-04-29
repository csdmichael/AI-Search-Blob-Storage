# Determine app root — Oryx may extract to a temp dir
APP_DIR="${APP_PATH:-/home/site/wwwroot}"
cd "$APP_DIR"

export PYTHONPATH="${APP_DIR}:${APP_DIR}/.python_packages/lib/site-packages:${PYTHONPATH}"
gunicorn app:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 240 --chdir "$APP_DIR"
