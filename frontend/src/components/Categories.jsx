import React, { useState } from "react";
import {
  ChevronDown,
  ChevronRight,
  Users,
  GraduationCap,
  Calendar,
} from "lucide-react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

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

const studentChartData = [
  { name: "Academics & Unit Registration", value: 75 },
  { name: "Admissions & Enrollment", value: 10 },
  { name: "Examinations & Assessments", value: 10 },
  { name: "Finance & Fees", value: 5 },
];

const lecturerChartData = [
  { name: "Teaching & Course Management", value: 60 },
  { name: "Assessment & Examination Coordination", value: 25 },
  { name: "Administrative & HR-Related", value: 15 },
];

const COLORS = ["#2563EB", "#38BDF8", "#10B981", "#F59E0B", "#EF4444"];

export default function Categories() {
  const [openSection, setOpenSection] = useState({});
  const [timeFilter, setTimeFilter] = useState("This Month");

  const toggleSection = (role, index) => {
    setOpenSection((prev) => ({
      ...prev,
      [`${role}-${index}`]: !prev[`${role}-${index}`],
    }));
  };

  const handleClick = (sub) => {
    console.log("Clicked:", sub);
    // Placeholder for future modal or analytics tracking
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen overflow-hidden">
      {/* HEADER */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold text-blue-900">Categories Overview</h1>
        <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-xl shadow">
          <Calendar className="text-blue-700 w-5 h-5" />
          <select
            value={timeFilter}
            onChange={(e) => setTimeFilter(e.target.value)}
            className="bg-transparent outline-none text-gray-700"
          >
            <option>This Week</option>
            <option>This Month</option>
            <option>This Year</option>
          </select>
        </div>
      </div>

      {/* ANALYTICS SECTION */}
      <div className="grid md:grid-cols-2 gap-6 mb-10">
        <div className="bg-white p-4 rounded-2xl shadow-lg border border-blue-100">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">
            Student Category Trends
          </h2>
{/*           <ResponsiveContainer width="100%" height={250}> */}
{/*             <PieChart> */}
{/*               <Pie */}
{/*                 data={studentChartData} */}
{/*                 cx="50%" */}
{/*                 cy="50%" */}
{/*                 outerRadius={80} */}
{/*                 dataKey="value" */}
{/*               > */}
{/*                 {studentChartData.map((entry, index) => ( */}
{/*                   <Cell key={`s-${index}`} fill={COLORS[index % COLORS.length]} /> */}
{/*                 ))} */}
{/*               </Pie> */}
{/*               <Tooltip /> */}
{/*               <Legend /> */}
{/*             </PieChart> */}
{/*           </ResponsiveContainer> */}
        </div>

        <div className="bg-white p-4 rounded-2xl shadow-lg border border-blue-100">
          <h2 className="text-lg font-semibold text-blue-900 mb-3">
            Lecturer Category Trends
          </h2>
{/*           <ResponsiveContainer width="100%" height={250}> */}
{/*             <PieChart> */}
{/*               <Pie */}
{/*                 data={lecturerChartData} */}
{/*                 cx="50%" */}
{/*                 cy="50%" */}
{/*                 outerRadius={80} */}
{/*                 dataKey="value" */}
{/*               > */}
{/*                 {lecturerChartData.map((entry, index) => ( */}
{/*                   <Cell key={`l-${index}`} fill={COLORS[index % COLORS.length]} /> */}
{/*                 ))} */}
{/*               </Pie> */}
{/*               <Tooltip /> */}
{/*               <Legend /> */}
{/*             </PieChart> */}
{/*           </ResponsiveContainer> */}
        </div>
      </div>

      {/* CATEGORIES */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* STUDENTS */}
        <div className="bg-white rounded-2xl shadow-lg p-6 border border-blue-100 max-h-[70vh] overflow-y-auto">
          <div className="flex items-center mb-4 sticky top-0 bg-white pb-2">
            <GraduationCap className="text-blue-800 w-6 h-6 mr-2" />
            <h2 className="text-xl font-semibold text-blue-900">Students</h2>
          </div>

          {categories.Students.map((cat, index) => (
            <div key={index} className="mb-3 border-b border-gray-200 pb-2">
              <button
                className="flex justify-between w-full py-2 text-left font-medium text-gray-800 hover:text-blue-700 transition"
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
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {cat.sub.map((sub, i) => (
                    <button
                      key={i}
                      onClick={() => handleClick(sub)}
                      className="px-3 py-2 text-sm bg-blue-50 hover:bg-blue-100 text-blue-800 rounded-full transition font-medium shadow-sm hover:shadow-md"
                    >
                      {sub}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* LECTURERS */}
        <div className="bg-white rounded-2xl shadow-lg p-6 border border-blue-100 max-h-[70vh] overflow-y-auto">
          <div className="flex items-center mb-4 sticky top-0 bg-white pb-2">
            <Users className="text-blue-800 w-6 h-6 mr-2" />
            <h2 className="text-xl font-semibold text-blue-900">Lecturers</h2>
          </div>

          {categories.Lecturers.map((cat, index) => (
            <div key={index} className="mb-3 border-b border-gray-200 pb-2">
              <button
                className="flex justify-between w-full py-2 text-left font-medium text-gray-800 hover:text-blue-700 transition"
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
                <div className="grid grid-cols-2 gap-2 mt-2">
                  {cat.sub.map((sub, i) => (
                    <button
                      key={i}
                      onClick={() => handleClick(sub)}
                      className="px-3 py-2 text-sm bg-blue-50 hover:bg-blue-100 text-blue-800 rounded-full transition font-medium shadow-sm hover:shadow-md"
                    >
                      {sub}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
