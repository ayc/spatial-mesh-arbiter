import re

def main():
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'r') as f:
        content = f.read()

    # Thorns internal hit
    content = content.replace("""                            proc_depth: context.proc_depth.saturating_add(1),
                        }
                    }
                });""", """                            proc_depth: context.proc_depth.saturating_add(1),
                        }
                    })
                });""")

    # tick_status_effects internal hit
    content = content.replace("""                            payload: ActionPayload::Game(ArpgAction::InternalPreparedHit {
                                target_id: *entity_id,
                                context: context.clone(),
                            }
                        });""", """                            payload: ActionPayload::Game(ArpgAction::InternalPreparedHit {
                                target_id: *entity_id,
                                context: context.clone(),
                            })
                        });""")

    # Projectile Actor Impact Event
    content = content.replace("""                        damage_origin: self.damage_origin,
                        proc_depth: self.proc_depth,
                    }
                }
            });""", """                        damage_origin: self.damage_origin,
                        proc_depth: self.proc_depth,
                    }
                })
            });""")
            
    with open('docs/2-contracts-and-interfaces/internal-mesh-types/03-mesh-arbiter-state.md', 'w') as f:
        f.write(content)

if __name__ == '__main__':
    main()
