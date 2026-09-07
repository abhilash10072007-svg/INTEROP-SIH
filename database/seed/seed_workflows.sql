-- Sample workflow: RTO Driving License Renewal
with
    new_workflow as (
        insert into
            workflows (service_name, description)
        values (
                'Driving License Renewal',
                'Renew an expiring RTO-issued driving license'
            ) returning id
    )
insert into
    workflow_steps (
        workflow_id,
        step_order,
        step_name,
        step_type,
        auto_or_manual
    )
select
    id,
    step_order,
    step_name,
    step_type,
    auto_or_manual
from new_workflow, (
        values (
                1, 'document_upload', 'document_upload', 'auto'
            ), (
                2, 'fuzzy_match', 'identity_verification', 'auto'
            ), (
                3, 'risk_assessment', 'risk_check', 'auto'
            ), (
                4, 'official_review', 'review', 'manual'
            )
    ) as steps (
        step_order, step_name, step_type, auto_or_manual
    );

-- Sample workflow: Small Business Loan (Bank)
with
    new_workflow as (
        insert into
            workflows (service_name, description)
        values (
                'MSME Business Loan',
                'Apply for a small business loan under Udyam scheme'
            ) returning id
    )
insert into
    workflow_steps (
        workflow_id,
        step_order,
        step_name,
        step_type,
        auto_or_manual
    )
select
    id,
    step_order,
    step_name,
    step_type,
    auto_or_manual
from new_workflow, (
        values (
                1, 'document_upload', 'document_upload', 'auto'
            ), (
                2, 'fraud_check', 'fraud_check', 'auto'
            ), (
                3, 'risk_assessment', 'risk_check', 'auto'
            ), (
                4, 'official_review', 'review', 'manual'
            )
    ) as steps (
        step_order, step_name, step_type, auto_or_manual
    );