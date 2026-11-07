// Excerpt from FalconChristmas/fpp@49c9591f3ca33c023c804e5a124966aa132c7d12
// www/multisync.php lines 1696-1804, verbatim. GPL-2.0-or-later; the Falcon Player developers and contributors.
// Source entry [S1301]. See LICENSE-NOTE.md.
// lines 1696-1804
                            unavailables[ip]++;
                            status = "unreachable";
                        } else if (data.status_name == 'password') {
                            status = '<span class="text-danger">Protected</span>';
                        } else if (data.status_name == 'unknown') {
                            status = '-';
                        } else if ((data.status_name == 'idle') ||
                                   (data.status_name == 'playing media') ||
                                   (data.status_name == 'playing background')) {
                            // 'playing media'/'playing background' mean a stream
                            // slot is active outside a playlist.  The player is
                            // still idle, so a remote in this state may equally
                            // be syncing -- keep running the sync check below
                            // rather than falling through to the raw string,
                            // which would drop the "Syncing: <files>" detail.
                            if (data.status_name == 'playing media') {
                                status = 'Playing Media';
                            } else if (data.status_name == 'playing background') {
                                status = 'Background Audio';
                            }
                            if (data.mode_name == 'remote') {
                                if ((data.sequence_filename && data.sequence_filename != "") ||
                                    (data.media_filename && data.media_filename != "")) {
                                    status = 'Syncing';

                                    elapsed += data.time_elapsed;

                                    // Match players: visible text is the sequence
                                    // only, with the play icon (media tooltip)
                                    // after the name.  Media-only sync shows the
                                    // media as the text.
                                    if (data.sequence_filename && data.sequence_filename != "") {
                                        files += msEscape(data.sequence_filename);
                                    } else if (data.media_filename && data.media_filename != "") {
                                        files += msEscape(data.media_filename);
                                    }

                                    status = buildPlayingStatus(status, files, data.sequence_filename, data.media_filename);
                                }
                            } else if ((data.status_name == 'playing media') ||
                                       (data.status_name == 'playing background')) {
                                // Player/master playing standalone media (outside a
                                // playlist): same shape -- sequence (or media when
                                // there is no sequence) as text, play icon with
                                // media tooltip after the name.  A sequence here
                                // upgrades the label to "Playing Sequence".
                                var pfiles = "";
                                if (data.current_sequence && data.current_sequence != "") {
                                    pfiles += msEscape(data.current_sequence);
                                    status = 'Playing Sequence';
                                } else if (data.current_song && data.current_song != "") {
                                    pfiles += msEscape(data.current_song);
                                }

                                status = buildPlayingStatus(status, pfiles, data.current_sequence, data.current_song);
                                if (data.time_elapsed && data.time_elapsed != "" && data.time_elapsed != "00:00")
                                    elapsed = data.time_elapsed;
                            }
                        } else {
                            status = msEscape(data.status_name);
                        }
                        if (data.status_name != 'unreachable') {
                            unavailables[ip] = 0;
                        }

                        // An FPP/OS update running on the remote (the same
                        // updateActivity that drives its own update banner).
                        // fppd usually keeps running for most of an update, so
                        // status_name alone reads "Idle".  A player still
                        // playing keeps its playing status with the update
                        // noted underneath; anything else becomes "Upgrading".
                        // Either form links to the remote's live update log.
                        var ua = data.updateActivity;
                        if (ua && ua.inProgress && data.status_name != 'unreachable' && data.status_name != 'password') {
                            var uaDetail = msEscape(ua.kind || 'FPP Update');
                            if (ua.stage) {
                                uaDetail += ': ' + msEscape(ua.stage);
                            }
                            var uaHost = (data.advancedView && data.advancedView.HostName) ? data.advancedView.HostName : ip;
                            var uaLink = "<a href='#' class='msUpdateLogLink' title='View update log' data-ip='" + msEscape(ip) +
                                "' data-host='" + msEscape(uaHost) + "'>";
                            if (data.status_name == 'playing' || data.status_name == 'paused') {
                                status += "<br>" + uaLink + "<i class=\"fas fa-circle-notch fa-spin text-warning\"></i> <span class='warning-text'>" + uaDetail + "</span></a>";
                            } else {
                                status = uaLink + "<i class=\"fas fa-circle-notch fa-spin text-warning\"></i> Upgrading</a><br><small class='text-muted'>" + uaDetail + "</small>";
                            }
                        }

                        if (data.rebootFlag == 1) {
                            status += "<br><i class=\"fas fa-exclamation-triangle text-danger\"></i><span class='warning-text'>Device Reboot Required</span>";
                        }

                        if (data.restartFlag == 1) {
                            status += "<br><i class=\"fas fa-exclamation-triangle text-warning\"></i><span class='warning-text'>FPPD Restart Required</span>";
                        }

                        var hostRowKey = ip.replace(/\./g, '_');
                        var rowID = hostRows[hostRowKey];

                        var item = $('#fppSystemsTable').bootstrapTable('getRowByUniqueId', rowID);
                        if (!item) return;

                        var curStatus = item.status || '';
                        if (curStatus !== '' && curStatus.indexOf('Last Seen') === -1 && !refreshing) {
                            // Don't replace an existing status via a different IP
                            return;
                        }
                        if (status == 'unreachable') {
                            if (unavailables[ip] < 4) {
