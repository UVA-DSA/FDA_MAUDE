# Post-hoc statistics and tables for the da Vinci MAUDE malfunction analysis.
# Reads the classifier output (produced by src/classify_malfunctions.py) and
# writes the paper tables back into output/. Run from the repo root or from the
# analysis/ directory; the output directory is located relative to either.

# Which classified dataset to summarize. Must match END_YEAR in
# src/classify_malfunctions.py (set to 2013 for the original committed dataset).
end_year <- 2025

output_dir <- file.path("..", "output")
if (!dir.exists(output_dir)) output_dir <- "output"  # allow running from repo root

all_data <- read.csv(
    file.path(output_dir,
              paste0("daVinci_MDR_Malfunction_Impacts_", end_year, "_PLOS_One.csv")),
    fill = TRUE)

# Checked Broken cases and edited for PLOS_One

# 95% CI for proportion
p_confidence_interval <- function(a, n){
	CI <- round(1.96 * sqrt(a*(1-(a/n))) *(100/n),1)
	return(CI)
}

for (fname in c("Recent_Test.csv", "Remaining_Malfunctions.csv",
                "Table1.csv", "Table2.csv", "Table3.csv", "Table4.csv",
                "Table5.csv", "Table6.csv", "Table7.csv")) {
    file.create(file.path(output_dir, fname))
}

Malfunctions <- subset(all_data, Patient.Impact == "M")
Fallen <- subset(all_data, Fallen != "N/A")
System_Errors <- subset(all_data, System.Error != "N/A")
Moved <- subset(all_data, Moved != "N/A")
Broken <- subset(all_data, Broken != "N/A")
Arced <- subset(all_data, Arced != "N/A")
Tip_Cover <- subset(all_data, Tip.Cover != "N/A")
Vision <- subset(all_data, Vision != "N/A")
System_Reset <- subset(all_data, System.Reset != "N/A")
Converted <- subset(all_data, New.Converted != "N/A")
Rescheduled <- subset(all_data, New.Rescheduled != "N/A")

Rest_Malfunctions <- subset(all_data,(Patient.Impact == "M" & System.Error == "N/A" & 
                             Fallen == "N/A" & Arced == "N/A" & Tip.Cover == "N/A"  & 
				     Vision == "N/A" & Moved == "N/A") | 
				     Other != "N/A");

dim(Fallen)[1]
dim(System_Errors)[1]
dim(Arced)[1]
dim(Broken)[1]
dim(Tip_Cover)[1]
dim(Vision)[1]
dim(Moved)[1]
dim(all_data)[1] - dim(Rest_Malfunctions)[1]

Class <- vector("list",9)
Class[[1]] <- subset(all_data, System.Error != "N/A")
Class[[2]] <- subset(all_data, Fallen != "N/A")
Class[[3]] <- subset(all_data, Arced != "N/A" | Tip.Cover != "N/A")
Class[[4]] <- subset(all_data, Moved != "N/A")
Class[[5]] <- subset(all_data, Vision != "N/A")
Class[[6]] <- subset(all_data, Broken != "N/A")
# Other Malfunctions (Not above cases but indicated as "M" or Broken)
Class[[7]] <- subset(all_data, Other != "N/A")
# Total malfunctions found (Union of all the classes)
Class[[8]] <- subset(all_data, System.Error != "N/A" | Fallen != "N/A" | Broken != "N/A" | Arced != "N/A" | Tip.Cover != "N/A"  | Vision != "N/A" | Moved != "N/A" | Other != "N/A")
Class[[9]] <- all_data;

# Malfunction Impacts - Table 1 in the paper
Malfunction_Categories <- c("System Errors", "%", "Fallen Pieces", "%", "Arced/TipCover", "%",  
                            "Unintended_Operation", "%", "Video_Imaging", "%","Broken","%",
				    "Other","%", "Total_Malfunc","%","Total_Reports","%")
Impacts <- c("Total_Num","System_Reset","Converted","Rescheduled","Malfunction","Injury","Death","Other")
table_1 <- matrix(0:0,18,8,dimnames=list(Malfunction_Categories,Impacts))
for(i in seq(1,18,2))
{
	index = floor((i+1)/2)
	# Column 1: Total number of reports 
	table_1[i,1]  <- dim(Class[[index]])[1]
	table_1[i+1,1]<- round((dim(Class[[index]])[1]/dim(all_data)[1])*100,1)

	# Column 2: Number of System Resets
	table_1[i,2]  <- dim(subset(Class[[index]], System.Reset != "N/A"))[1]
	table_1[i+1,2]<- round((dim(subset(Class[[index]], System.Reset != "N/A"))[1])/(dim(Class[[index]])[1])*100,1)

	# Column 3: Number of Conversions
	table_1[i,3]  <- dim(subset(Class[[index]], New.Converted != "N/A"))[1]
	table_1[i+1,3]<- round((dim(subset(Class[[index]], New.Converted != "N/A"))[1])/(dim(Class[[index]])[1])*100,1)

	# Column 4: Number of Reschedulings
	table_1[i,4]  <- dim(subset(Class[[index]], New.Rescheduled != "N/A"))[1]
	table_1[i+1,4]<- round((dim(subset(Class[[index]], New.Rescheduled != "N/A"))[1])/(dim(Class[[index]])[1])*100,1)

	# Colu	mn 5: Number of Malfunctions, Injuries, Deaths, and Other events reported
	table_1[i,5] <- dim(subset(Class[[index]], Patient.Impact == "M"))[1]
	table_1[i,6] <- dim(subset(Class[[index]], Patient.Impact == "IN"))[1]
	table_1[i,7] <- dim(subset(Class[[index]], Patient.Impact == "D"))[1]
	table_1[i,8] <- dim(subset(Class[[index]], Patient.Impact == "O"))[1]
}
#table_1[14,2]<- round((dim(subset(Class[[7]], System.Reset != "N/A"))[1])/(dim(all_data)[1])*100,1)
#table_1[14,3]<- round((dim(subset(Class[[7]], New.Converted != "N/A"))[1])/(dim(all_data)[1])*100,1)
#table_1[14,4]<- round((dim(subset(Class[[7]], New.Rescheduled != "N/A"))[1])/(dim(all_data)[1])*100,1)

table_1
write.csv(table_1, file = file.path(output_dir, "Table1.csv"))

# Interruptions
interrupted <- subset(all_data, System.Reset != "N/A" | New.Converted != "N/A" | New.Rescheduled != "N/A")
dim(interrupted)[1]
dim(interrupted)[1]/(dim(all_data)[1])*100
reset_convert <- subset(all_data, System.Reset != "N/A" & New.Converted != "N/A")
dim(reset_convert)[1]
reset_res <- subset(all_data, System.Reset != "N/A" & New.Rescheduled != "N/A")
dim(reset_res)[1]


# Errors and Imaging
error_imaging <- subset(all_data, System.Error != "N/A" | Vision != "N/A")
dim(error_imaging)[1]
dim(error_imaging)[1]/dim(all_data)[1]
dim(subset(error_imaging,System.Reset != "N/A"))[1]
dim(subset(error_imaging,System.Reset != "N/A"))[1]/dim(System_Reset)[1]
dim(subset(error_imaging,New.Converted != "N/A"))[1]
dim(subset(error_imaging,New.Converted != "N/A"))[1]/dim(Converted)[1]
dim(subset(error_imaging,New.Rescheduled != "N/A"))[1]
dim(subset(error_imaging,New.Rescheduled != "N/A"))[1]/dim(Rescheduled)[1]
dim(subset(error_imaging,Patient.Impact == "O"))[1]
dim(subset(error_imaging,Patient.Impact == "O"))[1]/dim(error_imaging)[1]


Surgery_Class <- vector("list",7)
Surgery_Class[[1]] <- subset(all_data, Surgery_Class == "Gynecologic")
Surgery_Class[[2]] <- subset(all_data, Surgery_Class == "Urologic")
Surgery_Class[[3]] <- subset(all_data, Surgery_Class == "Cardiothoracic")
Surgery_Class[[4]] <- subset(all_data, Surgery_Class == "Head and Neck")
Surgery_Class[[5]] <- subset(all_data, Surgery_Class == "General")
Surgery_Class[[6]] <- subset(all_data, Surgery_Class == "Colorectal")
# Class of Other (Surgery_Class = "N/A")
Surgery_Class[[7]] <- subset(all_data, Surgery_Class == "N/A")

Surgery_Names <- c("Gynecologic", "%", "CI-", "CI+", "Urologic", "%", "CI-", "CI+", "Cardiothoracic", "%", "CI-", "CI+", 
                   "Head and Neck", "%", "CI-", "CI+", "General", "%", "CI-", "CI+", "Colorectal","%","CI-", "CI+", 
			 "Other","%", "CI-", "CI+")
Field_Names <- c("Total","Deaths","Injuries","Malfunctions","Other","System Errors","Fallen","Arced","Moved","Vision","Converted","Reschedulued")
### Surgery Classes - Table 3 in the JAMA paper
table_3 <- matrix(0:0,28,12,dimnames=list(Surgery_Names,Field_Names))
for(i in seq(1,28,4))
{
	index = floor((i-1)/4)+1
	# Column 1: Total number of reports 
	# Percentages over all the adverse events
	table_3[i,1]  <- dim(Surgery_Class[[index]])[1]
	table_3[i+1,1]<- round((dim(Surgery_Class[[index]])[1]/dim(all_data)[1])*100,1)	
	table_3[i+2,1]<- table_3[i+1,1] - p_confidence_interval(table_3[i,1],dim(all_data)[1])
	table_3[i+3,1]<- table_3[i+1,1] + p_confidence_interval(table_3[i,1],dim(all_data)[1])

	# Columns 2-5: Number of Deaths, Injuries, Malfunctions reported 
	# Percentage over adverse events in that class
	table_3[i,2] <- dim(subset(Surgery_Class[[index]], Patient.Impact == "D"))[1]
	table_3[i+1,2] <- round((table_3[i,2]/table_3[i,1])*100,1)
	table_3[i+2,2]<- table_3[i+1,2] - p_confidence_interval(table_3[i,2],table_3[i,1])
	table_3[i+3,2]<- table_3[i+1,2] + p_confidence_interval(table_3[i,2],table_3[i,1])

	table_3[i,3] <- dim(subset(Surgery_Class[[index]], Patient.Impact == "IN"))[1]
	table_3[i+1,3] <- round((table_3[i,3]/table_3[i,1])*100,1)
	table_3[i+2,3]<- table_3[i+1,3] - p_confidence_interval(table_3[i,3],table_3[i,1])
	table_3[i+3,3]<- table_3[i+1,3] + p_confidence_interval(table_3[i,3],table_3[i,1])

	table_3[i,4] <- dim(subset(Surgery_Class[[index]], Patient.Impact == "M"))[1]
	table_3[i+1,4] <- round((table_3[i,4]/table_3[i,1])*100,1)
	table_3[i+2,4]<- table_3[i+1,4] - p_confidence_interval(table_3[i,4],table_3[i,1])
	table_3[i+3,4]<- table_3[i+1,4] + p_confidence_interval(table_3[i,4],table_3[i,1])

	table_3[i,5] <- dim(subset(Surgery_Class[[index]], Patient.Impact == "O"))[1]
	table_3[i+1,5] <- round((table_3[i,5]/table_3[i,1])*100,1)
	table_3[i+2,5]<- table_3[i+1,5] - p_confidence_interval(table_3[i,5],table_3[i,1])
	table_3[i+3,5]<- table_3[i+1,5] + p_confidence_interval(table_3[i,5],table_3[i,1])

	# Column 6-10: Number of Different Malfunctions 
	table_3[i,6]  <- dim(subset(Surgery_Class[[index]], System.Error != "N/A"))[1]
	table_3[i+1,6]<- round((table_3[i,6]/table_3[i,1])*100,1)
	table_3[i+2,6]<- table_3[i+1,6] - p_confidence_interval(table_3[i,6],table_3[i,1])
	table_3[i+3,6]<- table_3[i+1,6] + p_confidence_interval(table_3[i,6],table_3[i,1])

	table_3[i,7]  <- dim(subset(Surgery_Class[[index]], Fallen != "N/A" | Broken != "N/A"))[1]
	table_3[i+1,7]<- round((table_3[i,6]/table_3[i,1])*100,1)
	table_3[i+2,7]<- table_3[i+1,7] - p_confidence_interval(table_3[i,7],table_3[i,1])
	table_3[i+3,7]<- table_3[i+1,7] + p_confidence_interval(table_3[i,7],table_3[i,1])
	
	table_3[i,8]  <- dim(subset(Surgery_Class[[index]], Arced != "N/A" | Tip.Cover != "N/A"))[1]
	table_3[i+1,8]<- round((table_3[i,8]/table_3[i,1])*100,1)
	table_3[i+2,8]<- table_3[i+1,8] - p_confidence_interval(table_3[i,8],table_3[i,1])
	table_3[i+3,8]<- table_3[i+1,8] + p_confidence_interval(table_3[i,8],table_3[i,1])
	
	table_3[i,9]  <- dim(subset(Surgery_Class[[index]], Moved != "N/A"))[1]
	table_3[i+1,9]<- round((table_3[i,9]/table_3[i,1])*100,1)
	table_3[i+2,9]<- table_3[i+1,9] - p_confidence_interval(table_3[i,9],table_3[i,1])
	table_3[i+3,9]<- table_3[i+1,9] + p_confidence_interval(table_3[i,9],table_3[i,1])

	table_3[i,10]  <- dim(subset(Surgery_Class[[index]], Vision != "N/A"))[1]
	table_3[i+1,10]<- round((table_3[i,10]/table_3[i,1])*100,1)
	table_3[i+2,10]<- table_3[i+1,10] - p_confidence_interval(table_3[i,10],table_3[i,1])
	table_3[i+3,10]<- table_3[i+1,10] + p_confidence_interval(table_3[i,10],table_3[i,1])

	# Column 11: Number of Conversions
	table_3[i,11]  <- dim(subset(Surgery_Class[[index]], New.Converted != "N/A"))[1]
	table_3[i+1,11]<- round((table_3[i,11]/table_3[i,1])*100,1)
	table_3[i+2,11]<- table_3[i+1,11] - p_confidence_interval(table_3[i,11],table_3[i,1])
	table_3[i+3,11]<- table_3[i+1,11] + p_confidence_interval(table_3[i,11],table_3[i,1])

	# Column 12: Number of Reschedulings
	table_3[i,12]  <- dim(subset(Surgery_Class[[index]], New.Rescheduled != "N/A"))[1]
	table_3[i+1,12]<- round((table_3[i,12]/table_3[i,1])*100,1)
	table_3[i+2,12]<- table_3[i+1,12] - p_confidence_interval(table_3[i,12],table_3[i,1])
	table_3[i+3,12]<- table_3[i+1,12] + p_confidence_interval(table_3[i,12],table_3[i,1])
}
#table_3
write.csv(table_3, file = file.path(output_dir, "Table3.csv"))

write.csv(System_Errors, file = file.path(output_dir, "Recent_Test.csv"))
write.csv(Rest_Malfunctions, file = file.path(output_dir, "Remaining_Malfunctions.csv"))

library(limma)
System_Reset <- (all_data$System.Reset != 'N/A')
Converted <- (all_data$New.Converted != 'N/A')
Rescheduled <- (all_data$New.Rescheduled != 'N/A')
c1 <- cbind(System_Reset, Converted, Rescheduled)
a1 <- vennCounts(c1);
vennDiagram(a1)

System_Error <- (all_data$System.Error != 'N/A')
Fallen <- (all_data$Fallen != 'N/A')
Arcing_Instruments <- (all_data$Arced != 'N/A' | all_data$Tip.Cover != 'N/A')
Unintended_Operation <- (all_data$Moved != 'N/A')
Video_Imaging <- (all_data$Vision != 'N/A')
System_Error_Imaging <- (all_data$Vision != 'N/A' | all_data$System.Error != 'N/A')
Other <- (all_data$Other != 'N/A')
c2 <- cbind(System_Error_Imaging, Fallen, Arcing_Instruments, Other, Unintended_Operation)
a2 <- vennCounts(c2);
vennDiagram(a2)

dim(all_data)[1]-dim(subset(all_data, System.Error != "N/A" | Fallen != "N/A" | Broken != "N/A" | Arced != "N/A" | Tip.Cover != "N/A"  | Vision != "N/A" | Moved != "N/A"))[1]
Broken <- subset(all_data, Broken != "N/A")
Broken_System_Error <- subset(Broken, System.Error != "N/A")
Broken_Fallen <- subset(Broken, Fallen != "N/A")
Broken_Arced <- subset(Broken, Arced != "N/A" | Tip.Cover != "N/A")
Broken_Moved <- subset(Broken,Moved != "N/A")
Broken_Vision <- subset(Broken, Vision != "N/A")
Broken_Other <- subset(Broken, Other != "N/A")

Class[[1]] <- subset(all_data, System.Error != "N/A")
Class[[2]] <- subset(all_data, Fallen != "N/A")
Class[[3]] <- subset(all_data, Arced != "N/A" | Tip.Cover != "N/A")
Class[[4]] <- subset(all_data, Moved != "N/A")
Class[[5]] <- subset(all_data, Vision != "N/A")

(dim(Broken_System_Error)[1])
(dim(Broken_Fallen)[1])
(dim(Broken_Arced)[1])
(dim(Broken_Moved)[1])
(dim(Broken_Vision)[1])
(dim(Broken_Other)[1])

round((dim(Broken_System_Error)[1])/(dim(Class[[1]])[1])*100,1)
round((dim(Broken_Fallen)[1])/(dim(Class[[2]])[1])*100,1)
round((dim(Broken_Arced)[1])/(dim(Class[[3]])[1])*100,1)
round((dim(Broken_Moved)[1])/(dim(Class[[4]])[1])*100,1)
round((dim(Broken_Vision)[1])/(dim(Class[[5]])[1])*100,1)
round((dim(Broken_Other)[1])/(dim(Class[[7]])[1])*100,1)

impacted <- subset(all_data, System.Reset != "N/A" | New.Converted != "N/A" | New.Rescheduled != "N/A" | Patient.Impact == "IN" | Patient.Impact == "D")
interrupted <- subset(all_data, (System.Reset != "N/A" | New.Converted != "N/A" | New.Rescheduled != "N/A"))
sys_interrupted_errors <- subset(interrupted, System.Error != "N/A")
dim(sys_interrupted_errors)[1]/dim(interrupted)[1]
sys_errors <- subset(all_data, System.Error != "N/A")
sys_error_interrupted <- subset(sys_errors, (System.Reset != "N/A" | New.Converted != "N/A" | New.Rescheduled != "N/A"))
sys_error_converted <- subset(sys_errors, (New.Converted != "N/A"))
sys_error_rescheduled <- subset(sys_errors, (New.Rescheduled != "N/A"))
sys_error_reset <- subset(sys_errors, (System.Reset != "N/A"))
dim(sys_error_rescheduled)[1]/dim(sys_errors)[1]
dim(interrupted)[1]
dim(impacted)[1]
dim(impacted)[1]/(dim(all_data)[1])*100

#subset(interrupted, Patient.Impact == "M")
