# Generated manually for comprehensive performance optimization

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounting", "0002_default_chart_of_accounts"),
    ]

    operations = [
        # إضافة فهارس محسّنة على Account
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["parent"], name="acc_parent_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["branch"], name="acc_branch_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["current_balance"], name="acc_balance_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(fields=["created_at"], name="acc_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(
                fields=["account_type", "is_active"], name="acc_type_active_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="account",
            index=models.Index(
                fields=["branch", "account_type"], name="acc_br_type_idx"
            ),
        ),
        # إضافة فهارس محسّنة على Transaction
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["total_debit"], name="txn_debit_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["total_credit"], name="txn_credit_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["created_at"], name="txn_created_at_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["updated_at"], name="txn_updated_at_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["transaction_type", "date"], name="txn_type_date_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["status", "date"], name="txn_status_date_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(fields=["customer", "date"], name="txn_cust_date_idx"),
        ),
        migrations.AddIndex(
            model_name="transaction",
            index=models.Index(
                fields=["order", "transaction_type"], name="txn_order_type_idx"
            ),
        ),
        # إضافة فهارس على TransactionLine
        migrations.AddIndex(
            model_name="transactionline",
            index=models.Index(fields=["transaction"], name="txn_line_txn_idx"),
        ),
        migrations.AddIndex(
            model_name="transactionline",
            index=models.Index(fields=["account"], name="txn_line_acc_idx"),
        ),
        migrations.AddIndex(
            model_name="transactionline",
            index=models.Index(fields=["debit"], name="txn_line_debit_idx"),
        ),
        migrations.AddIndex(
            model_name="transactionline",
            index=models.Index(fields=["credit"], name="txn_line_credit_idx"),
        ),
        migrations.AddIndex(
            model_name="transactionline",
            index=models.Index(
                fields=["transaction", "account"], name="txn_line_txn_acc_idx"
            ),
        ),
    ]
