import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.agents.review import review_diff

sample_diff = '''
diff --git a/app/rag/bulk_export.py b/app/rag/bulk_export.py
new file mode 100644
+++ b/app/rag/bulk_export.py
@@ -0,0 +1,10 @@
+from app.db.session import SessionLocal
+
+def export_all_chunks(repo_name):
+    db = SessionLocal()
+    chunks = db.query(CodeChunk).filter(CodeChunk.repo_name == repo_name).all()
+    return chunks
'''

result = review_diff(diff=sample_diff, repo_name="codepilot-ops")

print("REVIEW RESULT")
print("=" * 50)
print(f"Overall: {result.overall_assessment}")
print(f"Summary: {result.summary}\n")
for f in result.findings:
    print(f"[{f.severity.upper()}] {f.file_path} ({f.line_hint or 'n/a'})")
    print(f"  Issue: {f.issue}")
    print(f"  Fix:   {f.suggestion}\n")
