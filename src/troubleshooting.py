"""Sample-only, deterministic guided troubleshooting workflows."""

WORKFLOWS = {
    "Wi-Fi connection": {
        "category": "Wi-Fi",
        "source": "wifi_troubleshooting_sample.txt",
        "steps": (
            "Turn Wi-Fi off, wait ten seconds, and turn it on again.",
            "If the campus network is listed, forget it and reconnect with your credentials.",
            "Check that your device's date and time are correct.",
            "Restart your device and try again.",
            "Check whether other devices nearby also have no internet. If they do, report the location to IT.",
        ),
    },
    "Student portal": {
        "category": "Student Portal",
        "source": "student_portal_sample.txt",
        "steps": (
            "Check that your device has an internet connection and reload the page.",
            "Confirm that the portal address matches the address provided by your university.",
            "Try a current browser or a private window to check whether a browser extension is interfering.",
            "If sign-in is rejected, check your username and password without sharing them.",
            "Use the portal's official account-recovery option if available. If the issue continues, note the time and error for IT.",
        ),
    },
    "University email": {
        "category": "University Email",
        "source": "university_email_sample.pdf",
        "steps": (
            "Check that Caps Lock is off and that you entered your full email address.",
            "If you forgot your password, use the reset option on the sign-in page.",
            "If the account was locked after failed attempts, wait fifteen minutes and try again.",
            "Try a private or incognito browser window.",
            "If the issue continues, note the error message for your support ticket.",
        ),
    },
    "Software installation": {
        "category": "Software Installation",
        "source": "software_installation_sample.txt",
        "steps": (
            "Check that the installer matches your device's operating system and hardware.",
            "Use an installer only from the software publisher or an organization-approved source.",
            "Review the displayed error and the publisher's documented requirements.",
            "Do not disable antivirus or other security controls to make an installer run.",
            "If administrator permission is requested, contact IT rather than trying to bypass the restriction.",
        ),
    },
    "Computer lab": {
        "category": "Computer Lab",
        "source": "computer_lab_sample.txt",
        "steps": (
            "Check whether other devices in the same area can connect.",
            "For a wired workstation, check that its network cable is seated.",
            "Restart the browser and retry the affected service.",
            "Do not change shared workstation or network settings without authorization.",
            "If the issue continues, note the room, workstation identifier, and approximate time for IT.",
        ),
    },
    "Learning management system": {
        "category": "LMS",
        "source": "lms_sample.txt",
        "steps": (
            "Check your internet connection and reload the page.",
            "Confirm that you are using the LMS address provided by your organization.",
            "Try a supported, up-to-date browser and a private window.",
            "Note the course, page, time, and exact error message.",
            "If the issue continues, contact LMS support or the IT helpdesk.",
        ),
    },
    "Lab booking": {
        "category": "Other",
        "source": "lab_booking_sample.txt",
        "steps": (
            "Confirm that you are using the official booking page provided by your organization.",
            "Check whether your selected date and time are still shown as available.",
            "Wait for a confirmation message and check the account used to submit the request.",
            "Do not assume the booking is confirmed if an error appears or no confirmation is shown.",
            "If the issue continues, note the request time and any error for the lab administrator or IT.",
        ),
    },
    "Account security": {
        "category": "Account Security",
        "source": "account_security_sample.txt",
        "steps": (
            "Do not approve a sign-in request that you did not initiate.",
            "Never share your password, recovery code, or one-time code.",
            "Open the account portal using an address you already trust, not a link in an unexpected message.",
            "If available, use the official password-reset flow from that trusted portal.",
            "If you suspect your account is compromised, contact IT promptly.",
        ),
    },
}
