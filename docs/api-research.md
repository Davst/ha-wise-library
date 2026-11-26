# OCLC Wise REST API and Bibliotheek AanZet

Researched 2026-11-26 using public primary sources only; no login, patron credentials, or private data used.

## Access requirements

Wise provides a patron REST API, but the documented API is not a keyless personal-account API. Every request needs a calculated `WISE_KEY`, using ApplicationName, API-ID and API-KEY. OCLC supplies these application credentials; API-KEY differs by Wise system and environment. Patron credentials alone therefore do not meet the documented access requirements. Whether OCLC will provision a personal Home Assistant application, with what terms or cost, is unknown. [OCLC Requirements](https://help.wise.oclc.org/Wise_Rest-API/002_Requirements)

Even public discovery endpoints require a valid WISE-KEY. Shared/patron endpoints also require user authentication. The older flow uses `/patron/authentication` and sends the returned token in `Authorization`; that token lasts until 23:59:59 of the current day. This is a documented legacy flow, not proof it accepts AanZet's current national login. [OCLC Authentication](https://help-nl.wise.oclc.org/Wise_Rest-API/40_Authentication)

## AanZet and modern SSO

AanZet states that it moved to the shared national login in May 2024 and that the website/My Menu and Bibliotheek Wise app support it. [AanZet login announcement](https://www.bibliotheekaanzet.nl/binnenkort-makkelijker-inloggen)

For external applications, Wise-IAM uses OIDC access, refresh and ID tokens. OCLC must configure application redirect/logout URLs and target library systems. The configuration endpoint is `/configuration/oidc-client?libraryId=...`, itself requiring WISE_KEY; it returns `wellknownOidcUrl` and `clientId`. Subsequent API requests use bearer access tokens alongside WISE_KEY. Thus modern SSO does not remove the application-registration requirement. The documentation does not establish an open self-service registration route. [OCLC external-app Wise-IAM documentation](https://help-nl.wise.oclc.org/Wise_Rest-API/Hoe_gebruik_ik_de_Wise-IAM_in_mijn_externe_applicatie%3F)

## Loans and holds

The public high-level documentation explicitly provides authenticated reads for a patron's current loans and holds:

- `GET /patron/{patronSystemId}/library/{libraryId}/loan`
- `GET /patron/{patronSystemId}/library/{libraryId}/hold`

The source has a missing closing brace in its printed examples; the paths above correct that apparent typographical error. It does not provide JSON response schemas, due-date field names or hold-status enums. Those should be verified against the installation's OpenAPI specification before implementation. [OCLC My Account API](https://help.wise.oclc.org/Wise_Rest-API/010_My_Account)

OCLC identifies the technical reference location as `https://{WISE-instance-url}/restapi/swagger-ui/index.html`. The actual current AanZet instance, library ID, schema, enabled capabilities, polling limits and provisionable OIDC client remain unverified in this research. [OCLC API presentation, technical-documentation slide](https://www.oclc.org/content/dam/campaign-landing-pages/nl/events/contactdag2023/presentations/OCLC-Contactdag-2023_Het-hoe-en-wat-van-API%27s_Nander-Lankhorst_Stephan-Dekker_Petra-Otten.pdf)

## Practical conclusion

An official API route exists for the desired loans/holds integration, subject to OCLC/library application access and modern SSO setup. There is no documented way to use it with only a patron login and no application key. This is a documentation conclusion, not a tested denial by the live AanZet server. Ask AanZet/OCLC for a personal integration key, its current library/system identifiers, an OIDC client configuration and the applicable OpenAPI reference before building an authenticated add-on.
