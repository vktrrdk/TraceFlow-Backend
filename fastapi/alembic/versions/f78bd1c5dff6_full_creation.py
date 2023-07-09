"""full creation

Revision ID: f78bd1c5dff6
Revises: 
Create Date: 2023-07-09 11:04:23.419321

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f78bd1c5dff6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "user",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String()),
        sa.Column("run_tokens", postgresql.ARRAY(sa.String())),
    )

    op.create_table(
        "runtoken",
        sa.Column("id", sa.String(), primary_key=True),
    )


    op.create_table(
        "run_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String()),
        sa.Column("token", sa.String()),
        sa.Column("run_name", sa.String()),
        sa.Column("timestamp", sa.DateTime(), default=sa.func.utcnow()),
        sa.Column("reference", sa.String(), nullable=True),
        sa.Column("command_line", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("script_file", sa.String(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
        sa.Column("nextflow_version", sa.String(), nullable=True),
    )

    op.create_table(
        "run_metric",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String()),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("run_name", sa.String()),
        sa.Column("timestamp", sa.DateTime(), default=sa.func.utcnow()),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("process", sa.String(), nullable=True),
        sa.Column("tag", sa.String(), nullable=True),
        sa.Column("cpus", sa.Integer(), nullable=True),
        sa.Column("memory", sa.Integer(), nullable=True),
        sa.Column("disk", sa.Integer(), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("script", sa.String(), nullable=True),
        sa.Column("time", sa.Integer(), nullable=True),
        sa.Column("realtime", sa.Integer(), nullable=True),
        sa.Column("cpu_percentage", sa.Float(precision=4), nullable=True),
        sa.Column("rchar", sa.Integer(), nullable=True),
        sa.Column("wchar", sa.Integer(), nullable=True),
        sa.Column("syscr", sa.Integer(), nullable=True),
        sa.Column("syscw", sa.Integer(), nullable=True),
        sa.Column("read_bytes", sa.Integer(), nullable=True),
        sa.Column("write_bytes", sa.Integer(), nullable=True),
        sa.Column("memory_percentage", sa.Float(precision=4), nullable=True),
        sa.Column("vmem", sa.Integer(), nullable=True),
        sa.Column("rss", sa.Integer(), nullable=True),
        sa.Column("peak_vmem", sa.Integer(), nullable=True),
        sa.Column("peak_rss", sa.Integer(), nullable=True),
        sa.Column("vol_ctxt", sa.Integer(), nullable=True),
        sa.Column("inv_ctxt", sa.Integer(), nullable=True),
        sa.Column("event", sa.String(), nullable=True),
    )

    op.create_table(
        "stat",
        sa.Column("succeeded_count", sa.Integer(), nullable=True),
        sa.Column("compute_time_fmt", sa.String(), nullable=True),
        sa.Column("cached_count", sa.Integer(), nullable=True),
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("run_metadata.id")),
        sa.Column("peak_running", sa.Integer(), nullable=True),
        sa.Column("succeeded_duration", sa.Integer(), nullable=True),
        sa.Column("cached_pct", sa.Float(precision=4), nullable=True),
        sa.Column("load_memory", sa.Integer(), nullable=True),
        sa.Column("succeed_count_fmt", sa.String(), nullable=True),
        sa.Column("failed_percentage", sa.Float(precision=4), nullable=True),
        sa.Column("ignored_count", sa.Integer(), nullable=True),
        sa.Column("submitted_count", sa.Integer(), nullable=True),
        sa.Column("running_count", sa.Integer(), nullable=True),
        sa.Column("peak_memory", sa.Integer(), nullable=True),
        sa.Column("succeed_percentage", sa.Float(precision=4), nullable=True),
        sa.Column("pending_count", sa.Integer(), nullable=True),
        sa.Column("load_cpus", sa.Integer(), nullable=True),
        sa.Column("cached_duration", sa.Integer(), nullable=True),
        sa.Column("aborted_count", sa.Integer(), nullable=True),
        sa.Column("failed_duration", sa.Integer(), nullable=True),
        sa.Column("failed_count", sa.Integer(), nullable=True),
        sa.Column("load_memory_fmt", sa.String(), nullable=True),
        sa.Column("retries_count", sa.Integer(), nullable=True),
        sa.Column("cached_count_fmt", sa.String(), nullable=True),
        sa.Column("process_length", sa.Integer(), nullable=True),
        sa.Column("peak_memory_fmt", sa.String(), nullable=True),
        sa.Column("failed_count_fmt", sa.String(), nullable=True),
        sa.Column("ignored_count_fmt", sa.String(), nullable=True),
        sa.Column("peak_cpus", sa.Integer(), nullable=True),
        sa.Column("ignored_percentage", sa.Float(precision=4), nullable=True),
    )

    op.create_table(
        "process",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), sa.ForeignKey("stat.id")),
        sa.Column("index", sa.Integer(), nullable=True),
        sa.Column("pending", sa.Integer(), nullable=True),
        sa.Column("ignored", sa.Integer(), nullable=True),
        sa.Column("load_cpus", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("succeeded", sa.Integer(), nullable=True),
        sa.Column("errored", sa.Boolean(), server_default=sa.sql.expression.false(), nullable=False),
        sa.Column("running", sa.Integer(), nullable=True),
        sa.Column("retries", sa.Integer(), nullable=True),
        sa.Column("peak_running", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("task_name", sa.String(), nullable=True),
        sa.Column("load_memory", sa.Integer(), nullable=True),
        sa.Column("stored", sa.Integer(), nullable=True),
        sa.Column("terminated", sa.Boolean(), server_default=sa.sql.expression.false(), nullable=False),
        sa.Column("process_hash", sa.String(), nullable=True),
        sa.Column("aborted", sa.Integer(), nullable=True),
        sa.Column("failed", sa.Integer(), nullable=True),
        sa.Column("peak_cpus", sa.Integer(), nullable=True),
        sa.Column("peak_memory", sa.Integer(), nullable=True),
        sa.Column("completed_count", sa.Integer(), nullable=True),
        sa.Column("cached", sa.Integer(), nullable=True),
        sa.Column("submitted", sa.Integer(), nullable=True),
    )

    op.create_foreign_key(
        "fk_stat_run_metadata",
        "stat",
        "run_metadata",
        ["parent_id"],
        ["id"],
    )

    op.create_foreign_key(
        "fk_process_stat",
        "process",
        "stat",
        ["parent_id"],
        ["id"],
    )
