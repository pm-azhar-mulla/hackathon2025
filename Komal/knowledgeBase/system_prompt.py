# Sample database schema copied from sql_query_agent.py
SAMPLE_SCHEMA = """
Table: campaign_site_ad_for_ecpm_update
Columns:
  - ga_campaign_id (BigInteger) - Ga Campaign ID
  - pm_ad_id (BigInteger) - Pm Ad ID
  - pm_site_id (BigInteger) - Pm Site ID
  - pub_id (BigInteger) - Pub ID

Table: wrapper_abtest_groupsize
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_abtest_type
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_ad_integration_type
Columns:
  - id (Integer, Primary Key) - ID
  - platform_id (Integer) - Platform ID
  - integration_type (Text) - Integration Type
  - method (Text) - Method
  - endpoint (Text) - Endpoint
  - endpoint_name (Text) - Endpoint Name
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - last_modified (DateTimeWithLocalTZ) - Last Modified

Table: wrapper_ad_parameter_dependency_map
Columns:
  - id (Integer, Primary Key) - ID
  - parent_object_group (Integer) - Parent Object Group
  - child_object_group (Integer) - Child Object Group

Table: wrapper_ad_parameter_group
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name

Table: wrapper_ad_parameter_tag_type_mapping
Columns:
  - id (BigInteger, Primary Key) - ID
  - parameter_id (BigInteger) - Parameter ID
  - tag_type_id (Integer) - Tag Type ID

Table: wrapper_ad_pod
Columns:
  - id (BigInteger, Primary Key) - ID
  - version_id (BigInteger) - Version ID
  - pod_type (Text) - Pod Type
  - ad_slots_config (Text) - Ad Slots Config
  - s2s_ad_slots_config (Text) - S2s Ad Slots Config
  - targeting (Text) - Targeting
  - creation_time (DateTimeWithLocalTZ) - Creation Time

Table: wrapper_ad_unit_config
Columns:
  - id (BigInteger, Primary Key) - ID
  - profile_id (BigInteger, Foreign Key to wrapper_profile.id) - Profile ID
  - ad_unit_id (BigInteger) - Ad Unit ID
  - config_id (Integer) - Config ID
  - value (Text) - Value

Table: wrapper_ad_unit_format
Columns:
  - id (Integer, Primary Key) - ID
  - name (Text) - Name
  - description (Text) - Description
  - display_name (Text) - Display Name

Table: wrapper_global_code_version
Columns:
  - id (BigInteger, Primary Key) - ID
  - is_live (Integer) - Is Live
  - prebid_base_version (Text) - Prebid Base Version
  - release_date (DateTimeWithLocalTZ) - Release Date
  - release_name (Text) - Release Name
  - release_notes_url (Text) - Release Notes URL
  - release_summary (Text) - Release Summary (details about this release)
  - release_type_id (Integer) - Release Type ID
  - snapshot_json (Text) - Snapshot Json
  - is_disabled (Integer) - Is Disabled (This column is used for disabling OpenWrap release versions)

Table: wrapper_live_code
Columns:
  - id (BigInteger, Primary Key) - ID
  - status (Text) - Status
  - created_at (DateTimeWithLocalTZ) - Created At
  - updated_at (DateTimeWithLocalTZ) - Updated At
  - version (Text) - Version of the live code
  - author (Text) - The author of the live code
  - is_active (Boolean) - Is Active (Indicates if the code version is currently active)

Table: wrapper_status
Columns:
  - cdn_refresh_id (BigInteger) - Cdn Refresh ID
  - modification_time (DateTimeWithLocalTZ) - Modification Time
  - status (Text) - Status (this shows status of wrapper, it could be live or staging or draft)
  - version_id (BigInteger, Foreign Key to wrapper_version.id) - Version ID

Table: wrapper_profile
Columns:
  - id (BigInteger, Primary Key) - ID
  - is_disabled (Integer) - Is Disabled
  - name (Text) - Name
  - pub_id (BigInteger) - Pub ID
  - type (Boolean) - Type (1 means OpenWrap and 2 means IDhub or identity hub)
  - api_version (Integer) - Api Version
  - platform (Text) - Platform
  - is_action_required (Integer) - Is Action Required

Table: wrapper_version
Columns:
  - id (BigInteger, Primary Key) - ID
  - profile_id (BigInteger, Foreign Key to wrapper_profile.id) - Profile ID
  - comment (Text) - Comment
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - display_version (BigInteger) - Display Version
  - last_modified (DateTimeWithLocalTZ) - Last Modified
  - script_size (Float) - Script Size

Table: wrapper_version_to_code_map
Columns:
  - version_id (BigInteger, Foreign Key to wrapper_version.id) - Version ID
  - global_code_version_id (BigInteger, Foreign Key to wrapper_global_code_version.id) - Global Code Version ID
  - code (Text) - Code
  - last_modified (DateTimeWithLocalTZ) - Last Modified

Table: wrapper_config_map
Columns:
  - id (BigInteger, Primary Key) - ID
  - config_id (Integer) - Config ID
  - entity_id (BigInteger) - Entity ID
  - entity_type_id (Integer) - Entity Type ID
  - partner_id (BigInteger) - Partner ID
  - value (Text) - Value
  - is_active (Boolean) - Is Active
  - test_config (Boolean) - Test Config
  - creation_time (DateTimeWithLocalTZ) - Creation Time
  - modification_time (DateTimeWithLocalTZ) - Modification Time
"""