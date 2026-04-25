import Sidebar from "../components/Sidebar";
import Topbar from "../components/Topbar";
import { useState } from "react";
import { Box } from "@mui/material";

export default function MainLayout({ children }) {
    const [mobileOpen, setMobileOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState("");


    const handleToggleSidebar = () => {
        setMobileOpen(!mobileOpen);
    };

    return (
        <Box sx={{ display: "flex" }}>
            <Topbar onMenuClick={handleToggleSidebar} onSearch={setSearchQuery}/>
            <Sidebar mobileOpen={mobileOpen} onClose={handleToggleSidebar}/>

            <Box 
                component="main"
                sx={{ flexGrow: 1, p: 3, mt: 8, ml: {sm: "240px"} }}>
                {children}
            </Box>
        </Box>
    );
}
