from vpnctl import rotate


def test_rotate_runs_steps_in_order():
    calls = []

    plan = rotate.rotate(
        provision_new=lambda: (calls.append("provision"), "203.0.113.99")[1],
        export_current_users=lambda: (calls.append("export"), ["u1", "u2"])[1],
        deploy_and_configure=lambda ip: calls.append(f"deploy:{ip}"),
        import_users=lambda ip, users: calls.append(f"import:{ip}:{len(users)}"),
        switch_subscription=lambda ip: (calls.append("switch"), True)[1],
        destroy_old=lambda ip: calls.append(f"destroy:{ip}"),
        old_ip="203.0.113.1",
    )

    assert plan.new_ip == "203.0.113.99"
    assert plan.users_migrated == 2
    assert plan.subscription_switched
    # экспорт до provision; destroy_old происходит последним
    assert calls == [
        "export",
        "provision",
        "deploy:203.0.113.99",
        "import:203.0.113.99:2",
        "switch",
        "destroy:203.0.113.1",
    ]


def test_rotate_reports_unswitched_subscription():
    plan = rotate.rotate(
        provision_new=lambda: "1.1.1.1",
        export_current_users=lambda: [],
        deploy_and_configure=lambda ip: None,
        import_users=lambda ip, users: None,
        switch_subscription=lambda ip: False,  # нет стабильного домена
        destroy_old=lambda ip: None,
        old_ip="2.2.2.2",
    )
    assert not plan.subscription_switched
