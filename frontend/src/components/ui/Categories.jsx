import React, { useState } from "react";
import { ChevronDown, ChevronRight, Users, GraduationCap } from "lucide-react";

const categories = {
  Students: [
    {
      main: "Admissions & Enrollment",
      sub: [
        "Application status inquiries",
        "Document submission or missing documents",
        "Admission offer acceptance or deferral",
        "Transfer or re-admission requests",
        "Change of program or major requests",
        "Entry requirements clarification",
        "Scholarship or financial aid related to admission",
        "Other",
      ],
    },
    {
      main: "Academics & Unit Registration",
      sub: [
        "Unit registration/add/drop requests",
        "Timetable or class schedule issues",
        "Prerequisite or unit eligibility questions",
        "Academic advising or guidance",
        "Class or lecture conflicts",
        "Change of academic load (full-time/part-time)",
        "Request for unit exemption or credit transfer",
        "Other",
      ],
    },
    {
      main: "Examinations & Assessments",
      sub: [
        "Exam timetable or venue inquiries",
        "Exam resit, deferral, or special consideration requests",
        "Grade or results queries",
        "Missing marks or incorrect grades",
        "Plagiarism or misconduct inquiries",
        "Other",
      ],
    },
    {
      main: "Graduation & Certificates",
      sub: [
        "Graduation application or clearance status",
        "Graduation ceremony details",
        "Transcript requests",
        "Degree certificate or diploma collection",
        "Verification of academic documents",
        "Other",
      ],
    },
    {
      main: "Finance & Fees",
      sub: [
        "Fee structure or payment plan inquiries",
        "Fee payment confirmation",
        "Refund or overpayment requests",
        "Scholarship disbursement issues",
        "Financial aid or bursary questions",
        "Outstanding balance or penalties",
        "Other",
      ],
    },
    {
      main: "Accommodation & Campus Services",
      sub: [
        "Hostel or housing applications",
        "Room change or maintenance issues",
        "Meal plan or cafeteria concerns",
        "Parking permits or campus transport",
        "Lost and found",
        "Other",
      ],
    },
    {
      main: "Student Welfare & Support",
      sub: [
        "Counseling or mental health support",
        "Medical or sick leave documentation",
        "Disability or special needs accommodation",
        "Personal issues affecting studies",
        "Student disciplinary matters",
        "Other",
      ],
    },
    {
      main: "International Students Office",
      sub: [
        "Visa and immigration guidance",
        "Study permit renewals",
        "International student orientation",
        "Travel or re-entry letters",
        "Cultural integration support",
        "Other",
      ],
    },
    {
      main: "Research & Postgraduate Affairs",
      sub: [
        "Thesis or dissertation submission",
        "Supervisor assignment or changes",
        "Research funding applications",
        "Ethics review or approval queries",
        "Conference or publication support",
        "Other",
      ],
    },
    {
      main: "Internships, Careers & Alumni",
      sub: [
        "Internship placement inquiries",
        "Attachment letter requests",
        "Job application verification letters",
        "Alumni record updates",
        "Career services or workshops",
        "Other",
      ],
    },
    {
      main: "General Administration & Communication",
      sub: [
        "Request for official letters",
        "Change of personal details",
        "Complaints or feedback",
        "Lost ID card replacement",
        "General inquiries or redirections",
        "Other",
      ],
    },
    { main: "Unclassified Emails", sub: [] },
  ],

  Lecturers: [
    {
      main: "Teaching & Course Management",
      sub: [
        "Course allocation or teaching load confirmation",
        "Request to change class schedule or venue",
        "Uploading materials to the LMS / e-learning issues",
        "Approval for field trips or guest lectures",
        "Request for additional tutorial or lab sessions",
        "Team-teaching coordination",
        "Other",
      ],
    },
    {
      main: "Assessment & Examination Coordination",
      sub: [
        "Submission of exam papers for moderation",
        "Requests for exam invigilators or substitutes",
        "Examination irregularity reports",
        "Grading submission issues",
        "Request for grade change approval",
        "Continuous assessment scheduling",
        "Other",
      ],
    },
    {
      main: "Administrative & HR-Related",
      sub: [
        "Leave applications",
        "Contract renewal or employment status inquiries",
        "Teaching assistant or graduate assistant requests",
        "Payroll, salary, or allowance issues",
        "ID card renewal or access permissions",
        "Staff evaluation or appraisal forms",
        "Other",
      ],
    },
    {
      main: "Faculty Meetings & Departmental Coordination",
      sub: [
        "Agenda items or minutes submission",
        "Meeting attendance confirmations",
        "Departmental report submissions",
        "Committee membership updates",
        "Requests for departmental budget items",
        "Other",
      ],
    },
    {
      main: "IT, Systems & Facilities",
      sub: [
        "LMS or grade submission system issues",
        "Request for access to lab or special equipment",
        "Software installation or licensing requests",
        "AV or projector malfunction reports",
        "Request for new email accounts or password resets",
        "Other",
      ],
    },
    {
      main: "Complaints, Feedback & Suggestions",
      sub: [
        "Student behavior or classroom management issues",
        "Policy or administrative concern escalation",
        "Feedback on institutional processes",
        "Requests for clarification on new regulations",
      ],
    },
    { main: "Unclassified Emails", sub: [] },
  ],
};

export default function Categories() {
  const [openSection, setOpenSection] = useState({});

  const toggleSection = (role, index) => {
    setOpenSection((prev) => ({
      ...prev,
      [`${role}-${index}`]: !prev[`${role}-${index}`],
    }));
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <h1 className="text-3xl font-bold text-blue-900 mb-8">
        Categories Overview
      </h1>

      <div className="grid md:grid-cols-2 gap-6">
        {/* STUDENT SECTION */}
        <div className="bg-white rounded-2xl shadow-lg p-4 border border-blue-100">
          <div className="flex items-center mb-4">
            <GraduationCap className="text-blue-800 w-6 h-6 mr-2" />
            <h2 className="text-xl font-semibold text-blue-900">Students</h2>
          </div>
          {categories.Students.map((cat, index) => (
            <div key={index} className="mb-2 border-b border-gray-200">
              <button
                className="flex justify-between w-full py-2 text-left font-medium text-gray-800 hover:text-blue-700"
                onClick={() => toggleSection("Students", index)}
              >
                {cat.main}
                {openSection[`Students-${index}`] ? (
                  <ChevronDown />
                ) : (
                  <ChevronRight />
                )}
              </button>
              {openSection[`Students-${index}`] && (
                <ul className="ml-4 mb-3 list-disc text-sm text-gray-600 space-y-1">
                  {cat.sub.map((sub, i) => (
                    <li key={i}>{sub}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>

        {/* LECTURER SECTION */}
        <div className="bg-white rounded-2xl shadow-lg p-4 border border-blue-100">
          <div className="flex items-center mb-4">
            <Users className="text-blue-800 w-6 h-6 mr-2" />
            <h2 className="text-xl font-semibold text-blue-900">Lecturers</h2>
          </div>
          {categories.Lecturers.map((cat, index) => (
            <div key={index} className="mb-2 border-b border-gray-200">
              <button
                className="flex justify-between w-full py-2 text-left font-medium text-gray-800 hover:text-blue-700"
                onClick={() => toggleSection("Lecturers", index)}
              >
                {cat.main}
                {openSection[`Lecturers-${index}`] ? (
                  <ChevronDown />
                ) : (
                  <ChevronRight />
                )}
              </button>
              {openSection[`Lecturers-${index}`] && (
                <ul className="ml-4 mb-3 list-disc text-sm text-gray-600 space-y-1">
                  {cat.sub.map((sub, i) => (
                    <li key={i}>{sub}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
