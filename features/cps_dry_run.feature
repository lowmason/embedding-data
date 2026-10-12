Feature: Preview CPS extract definitions
  Review the selected samples before requesting data from IPUMS.

  Background:
    Given this CPS sample catalog:
      | sample_id   | description                |
      | cps2024_12b | December 2024 Basic Monthly |
      | cps2025_01s | January 2025 Supplement     |
      | cps2025_01b | January 2025 Basic Monthly  |
      | cps2024_03s | March 2024 ASEC             |
      | cps2025_03s | March 2025 ASEC             |
      | cps2026_03s | March 2026 ASEC             |
      | cps2026_08b | August 2026 Basic Monthly   |
      | cps2026_09s | September 2026 Supplement   |

  Scenario: Preview both extract sets by default
    When I preview the default CPS extracts
    Then the "monthly" definition contains these samples in order:
      | sample_id   |
      | cps2025_01b |
      | cps2026_08b |
      | cps2026_09s |
    And the "asec" definition contains these samples in order:
      | sample_id   |
      | cps2025_03s |
      | cps2026_03s |
    And no extracts are submitted or downloaded

  Scenario: Preview monthly samples from a later start
    When I preview monthly CPS extracts starting at "2026-08"
    Then the "monthly" definition contains these samples in order:
      | sample_id   |
      | cps2026_08b |
      | cps2026_09s |
    And no "asec" definition is written
    And no extracts are submitted or downloaded
