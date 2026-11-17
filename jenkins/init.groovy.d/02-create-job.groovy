#!groovy
import jenkins.model.*
import org.jenkinsci.plugins.workflow.job.WorkflowJob
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import hudson.plugins.git.GitSCM
import hudson.plugins.git.BranchSpec
import hudson.plugins.git.UserRemoteConfig
import hudson.triggers.SCMTrigger

def jenkins = Jenkins.getInstance()
def jobName = "WDI-ETL-Pipeline"
def repoUrl = "https://github.com/KumawatCodes/wdi-etl-pipeline.git"
def branchName = "*/master"
def pollSchedule = "H/3 * * * *"

println "--> Inspecting Pipeline Job: ${jobName}"

def job = jenkins.getItem(jobName)
if (job == null) {
    println "--> Creating new Pipeline Job: ${jobName}"
    job = jenkins.createProject(WorkflowJob.class, jobName)
}

// Configure Pipeline from Git SCM only if not already configured as SCM
def currentDef = job.getDefinition()
if (!(currentDef instanceof CpsScmFlowDefinition)) {
    println "--> Configuring Pipeline script from SCM for ${jobName}"
    def userRemoteConfigs = [new UserRemoteConfig(repoUrl, null, null, null)]
    def branches = [new BranchSpec(branchName)]
    def scm = new GitSCM(userRemoteConfigs, branches, false, [], null, null, [])
    def scmDefinition = new CpsScmFlowDefinition(scm, "Jenkinsfile")
    scmDefinition.setLightweight(true)
    job.setDefinition(scmDefinition)
} else {
    println "--> Pipeline script from SCM already configured for ${jobName}; preserving."
}

// Configure Poll SCM trigger with H/3 * * * *
def existingTrigger = job.getTriggers().values().find { it instanceof SCMTrigger }
if (existingTrigger == null || existingTrigger.getSpec() != pollSchedule) {
    println "--> Configuring SCMTrigger with schedule: ${pollSchedule}"
    job.addTrigger(new SCMTrigger(pollSchedule))
} else {
    println "--> SCMTrigger already configured with schedule: ${pollSchedule}; preserving."
}

job.save()
println "--> Pipeline Job '${jobName}' configuration successfully verified."
