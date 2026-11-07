# Excerpt from home-assistant/core@db50c01e164020f0179e679c9923138bf4172e9c
# homeassistant/components/wled/config_flow.py lines 77-91, verbatim. Apache-2.0; Home Assistant contributors.
# Source entry [S1300]. See LICENSE-NOTE.md.
# lines 77-91
                await self.async_set_unique_id(mac_address, raise_on_progress=False)
                if self.source == SOURCE_RECONFIGURE:
                    entry = self._get_reconfigure_entry()
                    self._abort_if_unique_id_mismatch(
                        reason="unique_id_mismatch",
                        description_placeholders={
                            "expected_mac": format_mac(entry.unique_id).upper(),
                            "actual_mac": mac_address.upper(),
                        },
                    )
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_HOST: host},
                    )
                self._abort_if_unique_id_configured(updates={CONF_HOST: host})
