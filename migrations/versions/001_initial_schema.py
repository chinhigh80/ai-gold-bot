"""Initial database schema

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("language_code", sa.String(10), nullable=False, server_default="en"),
        sa.Column("balance_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gold_grams", sa.Float(), nullable=False, server_default="0"),
        sa.Column("referral_code", sa.String(20), nullable=False),
        sa.Column("referred_by_id", sa.BigInteger(), nullable=True),
        sa.Column("referral_bonus_earned_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
        sa.UniqueConstraint("referral_code"),
        sa.ForeignKeyConstraint(["referred_by_id"], ["users.id"]),
    )
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"])

    # orders
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("order_type", sa.Enum("buy", "sell", name="ordertype"), nullable=False),
        sa.Column("grams", sa.Float(), nullable=False),
        sa.Column("price_per_gram_usd", sa.Float(), nullable=False),
        sa.Column("base_price_per_gram_usd", sa.Float(), nullable=False),
        sa.Column("total_usd", sa.Float(), nullable=False),
        sa.Column("markup_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("spread_percent", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum(
            "pending", "awaiting_payment", "price_locked", "paid",
            "processing", "completed", "cancelled", "failed", "expired",
            name="orderstatus"
        ), nullable=False, server_default="pending"),
        sa.Column("payment_id", sa.String(255), nullable=True),
        sa.Column("payment_url", sa.String(2048), nullable=True),
        sa.Column("payment_address", sa.String(255), nullable=True),
        sa.Column("crypto_currency", sa.String(20), nullable=True),
        sa.Column("crypto_amount", sa.Float(), nullable=True),
        sa.Column("withdrawal_crypto", sa.String(20), nullable=True),
        sa.Column("withdrawal_wallet", sa.String(255), nullable=True),
        sa.Column("price_locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("price_lock_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_payment_id", "orders", ["payment_id"])

    # transactions
    op.create_table(
        "transactions",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("transaction_type", sa.Enum(
            "buy", "sell", "deposit", "withdrawal", "referral_bonus", "admin_credit", "admin_debit",
            name="transactiontype"
        ), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("gold_grams", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("pending", "completed", "failed", "reversed", name="transactionstatus"), nullable=False, server_default="pending"),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("balance_before_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("balance_after_usd", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gold_before", sa.Float(), nullable=False, server_default="0"),
        sa.Column("gold_after", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_transactions_user_id", "transactions", ["user_id"])

    # withdrawals
    op.create_table(
        "withdrawals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("gold_grams", sa.Float(), nullable=False),
        sa.Column("crypto_type", sa.String(20), nullable=False),
        sa.Column("wallet_address", sa.String(255), nullable=False),
        sa.Column("crypto_amount", sa.Float(), nullable=True),
        sa.Column("crypto_price_at_request", sa.Float(), nullable=True),
        sa.Column("gold_price_per_gram_usd", sa.Float(), nullable=False),
        sa.Column("spread_percent", sa.Float(), nullable=False),
        sa.Column("status", sa.Enum(
            "pending", "approved", "processing", "completed", "rejected", "failed",
            name="withdrawalstatus"
        ), nullable=False, server_default="pending"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("tx_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_withdrawals_user_id", "withdrawals", ["user_id"])
    op.create_index("ix_withdrawals_status", "withdrawals", ["status"])

    # price_logs
    op.create_table(
        "price_logs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("price_per_oz_usd", sa.Float(), nullable=False),
        sa.Column("price_per_gram_usd", sa.Float(), nullable=False),
        sa.Column("aed_usd_rate", sa.Float(), nullable=False),
        sa.Column("source", sa.String(50), nullable=False, server_default="goldapi"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # admin_users
    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    # bot_settings
    op.create_table(
        "bot_settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("bot_settings")
    op.drop_table("admin_users")
    op.drop_table("price_logs")
    op.drop_table("withdrawals")
    op.drop_table("transactions")
    op.drop_table("orders")
    op.drop_table("users")

    # Drop enums
    for enum_name in ["ordertype", "orderstatus", "transactiontype", "transactionstatus", "withdrawalstatus"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
