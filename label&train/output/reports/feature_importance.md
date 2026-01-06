# Feature Importance (Logistic Regression Coefficients)

- 说明：权重来自 `LogisticRegression(multinomial)` 的系数；正权重表示更倾向该类别。
- 每类展示：Top-15 正向特征 + Top-15 负向特征。

## Class 0: normal

### Top-15 positive

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `tpl_af8954af` | 1.777491 | template | Instance spawned successfully. |
| 2 | `info_cnt` | 1.177840 | scalar |  |
| 3 | `tpl_bce59009` | 0.656292 | template | Neutron deleted interface <UUID>; detaching it from the instance and deleting it from the info cache |
| 4 | `tpl_428a3b40` | 0.269709 | template | Deleting instance files <PATH> |
| 5 | `tpl_fbe941c1` | 0.206331 | template | VM Resumed (Lifecycle Event) |
| 6 | `tpl_4d69fb36` | 0.156637 | template | Terminating instance |
| 7 | `tpl_c4268e60` | 0.102021 | template | Creating image |
| 8 | `tpl_c4693083` | 0.063525 | template | Claim successful on node parisaserver |
| 9 | `tpl_44540918` | 0.037291 | template | Took 51.93 seconds to build instance. |
| 10 | `tpl_40db3158` | 0.035445 | template | Took 45.58 seconds to spawn the instance on the hypervisor. |
| 11 | `tpl_1af0f082` | 0.035189 | template | Took 44.24 seconds to spawn the instance on the hypervisor. |
| 12 | `tpl_959a4a24` | 0.033949 | template | Took 51.22 seconds to build instance. |
| 13 | `tpl_6eeaee05` | 0.030091 | template | Took 36.94 seconds to build instance. |
| 14 | `tpl_5e07f916` | 0.027921 | template | Took 42.63 seconds to build instance. |
| 15 | `tpl_3482f9e3` | 0.026011 | template | Took 52.77 seconds to build instance. |

### Top-15 negative

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `tpl_7bb1bd13` | -1.254753 | template | VM Started (Lifecycle Event) |
| 2 | `tpl_fbd432b6` | -1.254753 | template | VM Paused (Lifecycle Event) |
| 3 | `error_cnt` | -1.122670 | scalar |  |
| 4 | `kw_Failed to start libvirt guest` | -0.979500 | keyword |  |
| 5 | `warn_cnt` | -0.830945 | scalar |  |
| 6 | `log_error_cnt` | -0.785591 | scalar |  |
| 7 | `total_records` | -0.775775 | scalar |  |
| 8 | `tpl_3f0cc10b` | -0.673052 | template | Deletion of <PATH> complete |
| 9 | `kw_qemu unexpectedly closed the monitor` | -0.600391 | keyword |  |
| 10 | `tpl_3de0f3e0` | -0.584086 | template | Took 7.73 seconds to spawn the instance on the hypervisor. |
| 11 | `tpl_e32dc0e7` | -0.584086 | template | Took 8.99 seconds to build instance. |
| 12 | `tpl_23c6f986` | -0.511891 | template | During sync_power_state the instance has a pending task (spawning). Skip. |
| 13 | `tpl_d2fe8513` | -0.445756 | template | Took 121.21 seconds to build instance. |
| 14 | `tpl_80ecbd68` | -0.445756 | template | Took 0.98 seconds to destroy the instance on the hypervisor. |
| 15 | `tpl_15c7e27c` | -0.445756 | template | Get console output |

## Class 1: fault_vm_destroy_after_create

### Top-15 positive

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `log_error_cnt` | 1.737206 | scalar |  |
| 2 | `tpl_23c6f986` | 0.983748 | template | During sync_power_state the instance has a pending task (spawning). Skip. |
| 3 | `kw_qemu unexpectedly closed the monitor` | 0.772751 | keyword |  |
| 4 | `tpl_00335c46` | 0.730395 | template | Took 0.11 seconds to destroy the instance on the hypervisor. |
| 5 | `tpl_62f854e0` | 0.713094 | template | Instance failed to spawn: nova.exception.FlavorDiskSmallerThanImage: Flavor's disk is too small for requested image. Fla… |
| 6 | `kw_FlavorDiskSmallerThanImage` | 0.713094 | keyword |  |
| 7 | `tpl_0aa941b3` | 0.713094 | template | Build of instance <UUID> aborted: Flavor's disk is too small for requested image. Flavor disk is <NUM> bytes, image is <… |
| 8 | `tpl_a03daa0f` | 0.711193 | template | VM Stopped (Lifecycle Event) |
| 9 | `tpl_05e0665b` | 0.672755 | template | Took 0.83 seconds to deallocate network for instance. |
| 10 | `tpl_0bc3f16d` | 0.661675 | template | error during stop() in sync_power_state.: nova.exception_Remote.UnexpectedTaskStateError_Remote: Conflict updating insta… |
| 11 | `tpl_683d6709` | 0.635358 | template | Took 1.84 seconds to deallocate network for instance. |
| 12 | `tpl_9d705987` | 0.634941 | template | Instance failed to spawn: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-12T17:06:… |
| 13 | `tpl_5de9f186` | 0.634941 | template | Failed to build and run instance: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-1… |
| 14 | `tpl_de1fc491` | 0.634941 | template | Failed to start libvirt guest: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-12T1… |
| 15 | `tpl_e9500b91` | 0.574236 | template | Took 0.12 seconds to destroy the instance on the hypervisor. |

### Top-15 negative

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `kw_VirtualInterfaceCreateException` | -0.888971 | keyword |  |
| 2 | `tpl_1cd7d3e7` | -0.714124 | template | Build of instance <UUID> aborted: Failed to allocate the network(s), not rescheduling.: nova.exception.BuildAbortExcepti… |
| 3 | `tpl_af8954af` | -0.566838 | template | Instance spawned successfully. |
| 4 | `tpl_c4268e60` | -0.553975 | template | Creating image |
| 5 | `tpl_86e61357` | -0.547118 | template | Instance destroyed successfully. |
| 6 | `log_total_records` | -0.526287 | scalar |  |
| 7 | `tpl_5a910f97` | -0.399494 | template | Received unexpected event network-vif-unplugged-<UUID> for instance with vm_state active and task_state None. |
| 8 | `tpl_c4d2619c` | -0.366170 | template | Took 0.67 seconds to destroy the instance on the hypervisor. |
| 9 | `tpl_32c22386` | -0.366170 | template | Took 0.19 seconds to destroy the instance on the hypervisor.\nTraceback (most recent call last):\n  File "<PATH>", line … |
| 10 | `tpl_832efa0c` | -0.366166 | template | Took 3.06 seconds to deallocate network for instance. |
| 11 | `tpl_428a3b40` | -0.353904 | template | Deleting instance files <PATH> |
| 12 | `tpl_c3072d13` | -0.340918 | template | Took 0.23 seconds to deallocate network for instance. |
| 13 | `tpl_4d69fb36` | -0.334251 | template | Terminating instance |
| 14 | `kw_Failed to allocate network` | -0.247947 | keyword |  |
| 15 | `tpl_e4ad4519` | -0.247067 | template | Failed to allocate network(s): nova.exception.VirtualInterfaceCreateException: Virtual Interface creation failed |

## Class 2: fault_network_dhcpoff

### Top-15 positive

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `kw_VirtualInterfaceCreateException` | 1.525044 | keyword |  |
| 2 | `tpl_e4ad4519` | 0.802474 | template | Failed to allocate network(s): nova.exception.VirtualInterfaceCreateException: Virtual Interface creation failed |
| 3 | `tpl_5a357ef2` | 0.802474 | template | Instance failed to spawn: nova.exception.VirtualInterfaceCreateException: Virtual Interface creation failed |
| 4 | `kw_Failed to allocate network` | 0.799962 | keyword |  |
| 5 | `tpl_1cd7d3e7` | 0.799497 | template | Build of instance <UUID> aborted: Failed to allocate the network(s), not rescheduling.: nova.exception.BuildAbortExcepti… |
| 6 | `error_cnt` | 0.517009 | scalar |  |
| 7 | `kw_BuildAbortException` | 0.483276 | keyword |  |
| 8 | `log_error_cnt` | 0.455714 | scalar |  |
| 9 | `tpl_3f0cc10b` | 0.442076 | template | Deletion of <PATH> complete |
| 10 | `tpl_a03daa0f` | 0.225441 | template | VM Stopped (Lifecycle Event) |
| 11 | `tpl_7bb1bd13` | 0.194647 | template | VM Started (Lifecycle Event) |
| 12 | `tpl_fbd432b6` | 0.194647 | template | VM Paused (Lifecycle Event) |
| 13 | `tpl_b97c6614` | 0.118055 | template | Took 0.18 seconds to destroy the instance on the hypervisor. |
| 14 | `tpl_428a3b40` | 0.101458 | template | Deleting instance files <PATH> |
| 15 | `tpl_c4268e60` | 0.083592 | template | Creating image |

### Top-15 negative

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `kw_Failed to start libvirt guest` | -0.372593 | keyword |  |
| 2 | `warn_cnt` | -0.351833 | scalar |  |
| 3 | `kw_qemu unexpectedly closed the monitor` | -0.320354 | keyword |  |
| 4 | `tpl_23c6f986` | -0.186735 | template | During sync_power_state the instance has a pending task (spawning). Skip. |
| 5 | `tpl_cb12e456` | -0.162882 | template | Instance failed block device setup: nova.exception.VolumeNotCreated: Volume <UUID> did not finish being created even aft… |
| 6 | `tpl_7a088eb2` | -0.162882 | template | Build of instance <UUID> aborted: Volume <UUID> did not finish being created even after we waited 0 seconds or 1 attempt… |
| 7 | `tpl_87ff83ed` | -0.162882 | template | Booting with volume-backed-image <UUID> at <PATH> |
| 8 | `tpl_b07b829e` | -0.162882 | template | Ignoring supplied device name: <PATH> Libvirt can't honour user-supplied dev names |
| 9 | `info_cnt` | -0.161689 | scalar |  |
| 10 | `tpl_00335c46` | -0.161664 | template | Took 0.11 seconds to destroy the instance on the hypervisor. |
| 11 | `tpl_05e0665b` | -0.159990 | template | Took 0.83 seconds to deallocate network for instance. |
| 12 | `tpl_0aa941b3` | -0.153340 | template | Build of instance <UUID> aborted: Flavor's disk is too small for requested image. Flavor disk is <NUM> bytes, image is <… |
| 13 | `tpl_62f854e0` | -0.153340 | template | Instance failed to spawn: nova.exception.FlavorDiskSmallerThanImage: Flavor's disk is too small for requested image. Fla… |
| 14 | `kw_FlavorDiskSmallerThanImage` | -0.153340 | keyword |  |
| 15 | `tpl_6a8bbff6` | -0.119627 | template | Received unexpected event network-vif-unplugged-<UUID> for instance with vm_state building and task_state spawning. |

## Class 3: fault_libvirt_domain_undefine

### Top-15 positive

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `kw_Failed to start libvirt guest` | 1.225012 | keyword |  |
| 2 | `warn_cnt` | 1.183312 | scalar |  |
| 3 | `tpl_86e61357` | 0.788322 | template | Instance destroyed successfully. |
| 4 | `tpl_3de0f3e0` | 0.777274 | template | Took 7.73 seconds to spawn the instance on the hypervisor. |
| 5 | `tpl_e32dc0e7` | 0.777274 | template | Took 8.99 seconds to build instance. |
| 6 | `tpl_7bb1bd13` | 0.724633 | template | VM Started (Lifecycle Event) |
| 7 | `tpl_fbd432b6` | 0.724633 | template | VM Paused (Lifecycle Event) |
| 8 | `tpl_5a910f97` | 0.666797 | template | Received unexpected event network-vif-unplugged-<UUID> for instance with vm_state active and task_state None. |
| 9 | `tpl_900f315e` | 0.594910 | template | Instance is already powered off in the hypervisor when stop is called. |
| 10 | `total_records` | 0.547351 | scalar |  |
| 11 | `tpl_3f0cc10b` | 0.476523 | template | Deletion of <PATH> complete |
| 12 | `log_total_records` | 0.464212 | scalar |  |
| 13 | `tpl_30a01980` | 0.431895 | template | During sync_power_state the instance has a pending task (deleting). Skip. |
| 14 | `tpl_11ea3790` | 0.409929 | template | Took 0.14 seconds to destroy the instance on the hypervisor. |
| 15 | `tpl_8719aa7b` | 0.401902 | template | Took 0.15 seconds to destroy the instance on the hypervisor. |

### Top-15 negative

| rank | feature | weight | kind | template_text (if tpl_*) |
|---:|---|---:|---|---|
| 1 | `log_error_cnt` | -1.407329 | scalar |  |
| 2 | `tpl_af8954af` | -1.106842 | template | Instance spawned successfully. |
| 3 | `kw_BuildAbortException` | -0.893874 | keyword |  |
| 4 | `info_cnt` | -0.823862 | scalar |  |
| 5 | `tpl_a03daa0f` | -0.705556 | template | VM Stopped (Lifecycle Event) |
| 6 | `tpl_0bc3f16d` | -0.666635 | template | error during stop() in sync_power_state.: nova.exception_Remote.UnexpectedTaskStateError_Remote: Conflict updating insta… |
| 7 | `tpl_bce59009` | -0.649061 | template | Neutron deleted interface <UUID>; detaching it from the instance and deleting it from the info cache |
| 8 | `kw_VirtualInterfaceCreateException` | -0.645107 | keyword |  |
| 9 | `tpl_683d6709` | -0.627297 | template | Took 1.84 seconds to deallocate network for instance. |
| 10 | `tpl_9d705987` | -0.619898 | template | Instance failed to spawn: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-12T17:06:… |
| 11 | `tpl_5de9f186` | -0.619898 | template | Failed to build and run instance: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-1… |
| 12 | `tpl_de1fc491` | -0.619898 | template | Failed to start libvirt guest: libvirt.libvirtError: internal error: qemu unexpectedly closed the monitor: <NUM>-04-12T1… |
| 13 | `tpl_e4ad4519` | -0.578690 | template | Failed to allocate network(s): nova.exception.VirtualInterfaceCreateException: Virtual Interface creation failed |
| 14 | `tpl_5a357ef2` | -0.578690 | template | Instance failed to spawn: nova.exception.VirtualInterfaceCreateException: Virtual Interface creation failed |
| 15 | `tpl_e9500b91` | -0.538358 | template | Took 0.12 seconds to destroy the instance on the hypervisor. |
