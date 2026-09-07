insert into
    mock_gov_uidai (
        aadhaar_number,
        name,
        dob,
        address
    )
values (
        '123456789012',
        'Ravi Kumar',
        '1990-05-14',
        '12 MG Road, Coimbatore, Tamil Nadu'
    ),
    (
        '234567890123',
        'Priya Sundaram',
        '1995-11-02',
        '45 Anna Nagar, Chennai, Tamil Nadu'
    ),
    (
        '345678901234',
        'Arun Vel',
        '1988-03-21',
        '7 Race Course Road, Coimbatore, Tamil Nadu'
    ) on conflict (aadhaar_number) do nothing;